<?php
/**
 * Plugin Name: SEO Machine - Yoast REST API Support
 * Description: Exposes Yoast SEO meta fields via the WordPress REST API for the SEO Machine tool.
 * Version: 1.6
 * Author: SEO Machine
 *
 * Installation:
 * 1. Upload this file to: wp-content/mu-plugins/seo-machine-yoast-rest.php
 * 2. That's it - mu-plugins are automatically activated
 *
 * If the mu-plugins folder doesn't exist, create it.
 */

// Prevent direct access
if (!defined('ABSPATH')) {
    exit;
}

/**
 * Register deterministic publication metadata used to reconcile ambiguous REST timeouts.
 */
add_action('init', function() {
    $publication_meta_fields = [
        'seo_machine_publication_key' => 'SEO Machine Publication Key',
        'seo_machine_source_sha256' => 'SEO Machine Source SHA-256',
    ];

    foreach (['post', 'page'] as $post_type) {
        foreach ($publication_meta_fields as $meta_key => $description) {
            register_post_meta($post_type, $meta_key, [
                'show_in_rest' => true,
                'single' => true,
                'type' => 'string',
                'description' => $description,
                'sanitize_callback' => function($value) {
                    $candidate = strtolower(trim((string) $value));
                    return preg_match('/^[0-9a-f]{64}$/', $candidate) ? $candidate : '';
                },
                'auth_callback' => function() {
                    return current_user_can('edit_posts');
                },
            ]);
        }
    }
});

/**
 * Find an existing post or page bound to a deterministic publication key.
 */
function seo_machine_find_publication($post_type, $publication_key) {
    $posts = get_posts([
        'post_type' => $post_type,
        'post_status' => ['draft', 'pending', 'future', 'private', 'publish'],
        'posts_per_page' => 2,
        'fields' => 'ids',
        'meta_key' => 'seo_machine_publication_key',
        'meta_value' => $publication_key,
        'no_found_rows' => true,
        'suppress_filters' => false,
    ]);
    return count($posts) >= 1 ? (int) $posts[0] : 0;
}

/**
 * Build the durable option key used as the publication reservation's unique key.
 * This retains compatibility with earlier plugin workers during rolling deployment.
 */
function seo_machine_publication_reservation_name($publication_key) {
    return 'seo_machine_publication_lock_' . $publication_key;
}

function seo_machine_publication_reservation_value(
    $reservation_token,
    $source_sha256,
    $post_type
) {
    return wp_json_encode([
        'schema' => 'seo-machine-publication-reservation/v1',
        'token' => $reservation_token,
        'source_sha256' => $source_sha256,
        'post_type' => $post_type,
        'created_at' => time(),
    ]);
}

function seo_machine_decode_publication_reservation($reservation_value) {
    if (!is_string($reservation_value) || $reservation_value === '') {
        return null;
    }
    $record = json_decode($reservation_value, true);
    if (
        !is_array($record)
        || ($record['schema'] ?? '') !== 'seo-machine-publication-reservation/v1'
        || empty($record['token'])
        || !is_string($record['token'])
    ) {
        return null;
    }
    return $record;
}

/**
 * Atomically reserve one publication key. The reservation survives DB reconnects.
 */
function seo_machine_acquire_publication_reservation(
    $reservation_name,
    $reservation_token,
    $source_sha256,
    $post_type
) {
    $reservation_value = seo_machine_publication_reservation_value(
        $reservation_token,
        $source_sha256,
        $post_type
    );
    if (!is_string($reservation_value) || $reservation_value === '') {
        return false;
    }
    return add_option($reservation_name, $reservation_value, '', false);
}

/**
 * Release only the reservation owned by this request, using compare-and-delete.
 */
function seo_machine_release_publication_reservation(
    $reservation_name,
    $reservation_token
) {
    $current_value = get_option($reservation_name, null);
    $record = seo_machine_decode_publication_reservation($current_value);
    if (
        $record === null
        || !hash_equals($record['token'], (string) $reservation_token)
    ) {
        return false;
    }

    global $wpdb;
    $deleted = $wpdb->query(
        $wpdb->prepare(
            "DELETE FROM {$wpdb->options} WHERE option_name = %s AND option_value = %s",
            $reservation_name,
            $current_value
        )
    );
    if ($deleted === 1) {
        wp_cache_delete($reservation_name, 'options');
        return true;
    }
    return false;
}

/**
 * Reserve publication keys atomically across reconnects and concurrent REST requests.
 */
$GLOBALS['seo_machine_publication_reservations'] = [];
foreach (['post', 'page'] as $post_type) {
    add_filter("rest_pre_insert_{$post_type}", function($prepared_post, $request) use ($post_type) {
        if (!empty($prepared_post->ID)) {
            return $prepared_post;
        }
        $meta = $request->get_param('meta');
        if (!is_array($meta) || empty($meta['seo_machine_publication_key'])) {
            return $prepared_post;
        }
        $publication_key = strtolower(trim((string) $meta['seo_machine_publication_key']));
        $source_sha256 = strtolower(trim((string) ($meta['seo_machine_source_sha256'] ?? '')));
        if (
            !preg_match('/^[0-9a-f]{64}$/', $publication_key)
            || !preg_match('/^[0-9a-f]{64}$/', $source_sha256)
        ) {
            return new WP_Error(
                'seo_machine_publication_metadata_invalid',
                'Publication key and source SHA-256 must be 64 lowercase hexadecimal characters.',
                ['status' => 400]
            );
        }

        $reservation_name = seo_machine_publication_reservation_name($publication_key);
        $reservation_token = wp_generate_uuid4();
        $reserved = seo_machine_acquire_publication_reservation(
            $reservation_name,
            $reservation_token,
            $source_sha256,
            $post_type
        );
        if (!$reserved) {
            $existing_post_id = seo_machine_find_publication($post_type, $publication_key);
            if ($existing_post_id) {
                return new WP_Error(
                    'seo_machine_publication_exists',
                    'A post already exists for this publication key.',
                    ['status' => 409, 'existing_post_id' => $existing_post_id]
                );
            }
            $current_value = get_option($reservation_name, null);
            if ($current_value === null) {
                return new WP_Error(
                    'seo_machine_publication_reservation_unavailable',
                    'The durable publication reservation could not be created; no draft was created.',
                    ['status' => 503]
                );
            }
            $record = seo_machine_decode_publication_reservation($current_value);
            return new WP_Error(
                'seo_machine_publication_recovery_required',
                'A previous or concurrent request owns this publication key. Reconcile its outcome before clearing the durable reservation; do not retry blindly.',
                [
                    'status' => 409,
                    'reservation_name' => $reservation_name,
                    'reservation_created_at' => is_array($record) ? ($record['created_at'] ?? null) : null,
                    'recovery' => 'Confirm no publishing request is active and no matching post exists before an administrator removes the reservation.',
                ]
            );
        }

        // A prior request may have committed and released just before this reservation was added.
        $existing_post_id = seo_machine_find_publication($post_type, $publication_key);
        if ($existing_post_id) {
            seo_machine_release_publication_reservation(
                $reservation_name,
                $reservation_token
            );
            return new WP_Error(
                'seo_machine_publication_exists',
                'A post already exists for this publication key.',
                ['status' => 409, 'existing_post_id' => $existing_post_id]
            );
        }

        $request_id = spl_object_id($request);
        $GLOBALS['seo_machine_publication_reservations'][$request_id] = [
            'reservation_name' => $reservation_name,
            'reservation_token' => $reservation_token,
        ];
        return $prepared_post;
    }, 10, 2);

    add_action("rest_after_insert_{$post_type}", function($post, $request, $creating) {
        if (!$creating) {
            return;
        }
        $request_id = spl_object_id($request);
        $reservation = $GLOBALS['seo_machine_publication_reservations'][$request_id] ?? null;
        if (is_array($reservation)) {
            seo_machine_release_publication_reservation(
                $reservation['reservation_name'],
                $reservation['reservation_token']
            );
        }
        unset($GLOBALS['seo_machine_publication_reservations'][$request_id]);
    }, 10, 3);
}

/**
 * Ambiguous REST failures intentionally retain the durable reservation. WordPress can
 * persist a post before later term, media, additional-field, or metadata processing
 * returns an error. Without proven publication metadata, releasing here could permit a
 * retry to create a duplicate. An administrator must reconcile and clear that explicit
 * recovery blocker; successful creation releases owner-only in rest_after_insert_*.
 */
/**
 * Register Yoast SEO meta fields for REST API access
 */
add_action('init', function() {
    // Only proceed if Yoast is active
    if (!defined('WPSEO_VERSION')) {
        return;
    }

    $yoast_meta_fields = [
        '_yoast_wpseo_focuskw' => [
            'description' => 'Yoast SEO Focus Keyphrase',
            'single' => true,
        ],
        '_yoast_wpseo_title' => [
            'description' => 'Yoast SEO Title',
            'single' => true,
        ],
        '_yoast_wpseo_metadesc' => [
            'description' => 'Yoast SEO Meta Description',
            'single' => true,
        ],
        '_yoast_wpseo_linkdex' => [
            'description' => 'Yoast SEO Score',
            'single' => true,
        ],
        '_yoast_wpseo_content_score' => [
            'description' => 'Yoast Readability Score',
            'single' => true,
        ],
        '_yoast_wpseo_meta-robots-noindex' => [
            'description' => 'Yoast Robots Noindex',
            'single' => true,
        ],
    ];

    foreach (['post', 'page'] as $post_type) {
        foreach ($yoast_meta_fields as $meta_key => $args) {
            register_post_meta($post_type, $meta_key, [
                'show_in_rest' => true,
                'single' => $args['single'],
                'type' => 'string',
                'description' => $args['description'],
                'auth_callback' => function() {
                    return current_user_can('edit_posts');
                },
            ]);
        }
    }
});

/**
 * Alternative: Add Yoast fields to REST response and handle updates
 * This provides a cleaner API interface
 */
add_action('rest_api_init', function() {
    // Only proceed if Yoast is active
    if (!defined('WPSEO_VERSION')) {
        return;
    }

    // Register a custom field group for Yoast SEO
    register_rest_field(['post', 'page'], 'yoast_seo', [
        'get_callback' => function($post) {
            return [
                'focus_keyphrase' => get_post_meta($post['id'], '_yoast_wpseo_focuskw', true),
                'seo_title' => get_post_meta($post['id'], '_yoast_wpseo_title', true),
                'meta_description' => get_post_meta($post['id'], '_yoast_wpseo_metadesc', true),
                'robots_noindex' => get_post_meta($post['id'], '_yoast_wpseo_meta-robots-noindex', true) === '1',
            ];
        },
        'update_callback' => function($value, $post) {
            if (!current_user_can('edit_post', $post->ID)) {
                return new WP_Error('rest_forbidden', 'You do not have permission to edit this post.', ['status' => 403]);
            }

            if (isset($value['focus_keyphrase'])) {
                update_post_meta($post->ID, '_yoast_wpseo_focuskw', sanitize_text_field($value['focus_keyphrase']));
            }
            if (isset($value['seo_title'])) {
                update_post_meta($post->ID, '_yoast_wpseo_title', sanitize_text_field($value['seo_title']));
            }
            if (isset($value['meta_description'])) {
                update_post_meta($post->ID, '_yoast_wpseo_metadesc', sanitize_text_field($value['meta_description']));
            }
            if (isset($value['robots_noindex'])) {
                update_post_meta(
                    $post->ID,
                    '_yoast_wpseo_meta-robots-noindex',
                    rest_sanitize_boolean($value['robots_noindex']) ? '1' : '0'
                );
            }

            return true;
        },
        'schema' => [
            'type' => 'object',
            'properties' => [
                'focus_keyphrase' => ['type' => 'string'],
                'seo_title' => ['type' => 'string'],
                'meta_description' => ['type' => 'string'],
                'robots_noindex' => ['type' => 'boolean'],
            ],
        ],
    ]);
});
