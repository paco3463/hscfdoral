<?php
/**
 * Import / update the site from wordpress/dist/manifest.json (built by "python3 build/build.py --wp").
 *
 *   wp hscf sync manifest.json --dry-run      show what would change, change nothing
 *   wp hscf sync manifest.json                create and update pages and posts
 *   wp hscf sync manifest.json --force        also overwrite pages someone edited in WordPress
 *   wp hscf sync manifest.json --prune        also move generated pages that are no longer in the manifest to the trash
 *   wp hscf status                            last import, counts, pages edited in WordPress
 *
 * The same import runs over HTTPS: POST /wp-json/hscf/v1/sync (an administrator's Application Password),
 * body = the manifest JSON, optional ?dry=1&force=1&prune=1. This is how the automatic blog posts arrive.
 *
 * Only posts and pages this importer created (they carry the _hscf_path field) are ever changed.
 * Nothing else in WordPress is touched.
 */
if ( ! defined( 'ABSPATH' ) ) exit;

const HSCF_FORMAT = 'hscf-wp-1';

function hscf_find_by_path( $path ) {
	// Exact match on the stored address (the home page's address is the empty string, which WP_Query can't search for).
	global $wpdb;
	$id = $wpdb->get_var( $wpdb->prepare(
		"SELECT p.ID FROM {$wpdb->postmeta} m JOIN {$wpdb->posts} p ON p.ID = m.post_id
		 WHERE m.meta_key = '_hscf_path' AND m.meta_value = %s AND p.post_type IN ('page','post','en_post')
		 ORDER BY CASE WHEN p.post_status = 'trash' THEN 1 ELSE 0 END, p.ID LIMIT 1", $path ) );
	return (int) $id;
}

function hscf_import_author() {
	$u = get_current_user_id();
	if ( $u ) return $u;
	$admins = get_users( array( 'role' => 'administrator', 'number' => 1, 'orderby' => 'ID', 'fields' => 'ID' ) );
	return $admins ? (int) $admins[0] : 1;
}

function hscf_content_hash( $id ) {
	return md5( (string) get_post_field( 'post_content', $id, 'raw' ) );
}

function hscf_save_static( array $files ) {
	$old   = (array) get_option( 'hscf_static_index', array() );
	$index = array();
	foreach ( $files as $path => $content ) {
		$opt = 'hscf_static_' . md5( $path );
		$index[ $path ] = $opt;
		update_option( $opt, $content, false );
	}
	foreach ( $old as $path => $opt ) {
		if ( ! isset( $index[ $path ] ) ) delete_option( $opt );
	}
	update_option( 'hscf_static_index', $index, true );
}

/**
 * @param array $m    decoded manifest
 * @param array $opts dry (bool), force (bool), prune (bool)
 * @return array report
 */
function hscf_sync( array $m, array $opts = array() ) {
	$dry   = ! empty( $opts['dry'] );
	$force = ! empty( $opts['force'] );
	$prune = ! empty( $opts['prune'] );
	$r = array( 'dry_run' => $dry, 'created' => array(), 'updated' => array(), 'unchanged' => 0, 'kept_wp_edits' => array(),
		'kept_trashed' => array(), 'pruned' => array(), 'orphans' => array(), 'errors' => array() );

	if ( ( $m['format'] ?? '' ) !== HSCF_FORMAT || empty( $m['items'] ) || ! is_array( $m['items'] ) ) {
		$r['errors'][] = 'This is not an HSCF manifest (expected format ' . HSCF_FORMAT . ').';
		return $r;
	}
	foreach ( array( 'partials', 'static', 'redirects', 'settings' ) as $k ) {
		if ( ! isset( $m[ $k ] ) || ! is_array( $m[ $k ] ) ) { $r['errors'][] = "Manifest is missing \"$k\"."; return $r; }
	}

	// Raw HTML (scripts, SVG, data- attributes, JSON-LD) must be stored exactly as built.
	kses_remove_filters();
	remove_filter( 'content_save_pre', 'wp_filter_post_kses' );
	wp_defer_term_counting( true );

	$items = $m['items'];
	usort( $items, function ( $a, $b ) {
		return substr_count( $a['path'], '/' ) <=> substr_count( $b['path'], '/' ) ?: strcmp( $a['path'], $b['path'] );
	} );
	$ids    = array();   // path => post ID
	$author = hscf_import_author();
	$tz     = new DateTimeZone( $m['settings']['timezone_string'] ?? 'America/New_York' );

	foreach ( $items as $it ) {
		$path = (string) $it['path'];
		$id   = hscf_find_by_path( $path );
		$label = '/' . $path;
		$existed = (bool) $id;
		if ( $id ) {
			$ids[ $path ] = $id;
			$post = get_post( $id );
			if ( $post->post_status === 'trash' && ! $force ) { $r['kept_trashed'][] = $label; continue; }
			$same   = get_post_meta( $id, '_hscf_hash', true ) === $it['hash'];
			$edited = get_post_meta( $id, '_hscf_content_hash', true ) !== hscf_content_hash( $id );
			if ( ! $force ) {
				if ( $edited ) {
					// The page text was edited in WordPress: keep it, but still refresh the SEO head and language link.
					$r['kept_wp_edits'][] = $label;
					if ( ! $same && ! $dry ) hscf_write_meta( $id, $it, false );
					continue;
				}
				if ( $same && $post->post_status === 'publish' ) { $r['unchanged']++; continue; }
			}
		}
		$parent = 0;
		if ( $it['type'] === 'page' && ! empty( $it['parent'] ) ) {
			$parent = $ids[ $it['parent'] ] ?? hscf_find_by_path( $it['parent'] );
			if ( ! $parent && ! $dry ) { $r['errors'][] = "$label: parent page /{$it['parent']} is missing."; continue; }
		}
		if ( $dry ) {
			$r[ $id ? 'updated' : 'created' ][] = $label;
			if ( ! $id ) $ids[ $path ] = -1;
			continue;
		}
		$arr = array(
			'post_type' => $it['type'], 'post_status' => 'publish', 'post_title' => $it['title'], 'post_name' => $it['slug'],
			'post_content' => $it['main'], 'post_excerpt' => $it['excerpt'] ?? '', 'post_parent' => (int) $parent,
			'post_author' => $author, 'comment_status' => 'closed', 'ping_status' => 'closed', 'menu_order' => 0,
		);
		if ( ! empty( $it['date'] ) ) {
			$d = new DateTime( $it['date'], $tz );
			$arr['post_date']     = $d->format( 'Y-m-d H:i:s' );
			$arr['post_date_gmt'] = get_gmt_from_date( $arr['post_date'] );
			$arr['edit_date']     = true;
		}
		if ( $id ) {
			$arr['ID'] = $id;
			$res = wp_update_post( wp_slash( $arr ), true );
		} else {
			$res = wp_insert_post( wp_slash( $arr ), true );
		}
		if ( is_wp_error( $res ) ) { $r['errors'][] = "$label: " . $res->get_error_message(); continue; }
		$id = (int) $res;
		$ids[ $path ] = $id;
		$got = get_post( $id );
		if ( $got->post_name !== $it['slug'] ) {
			// WordPress renamed the slug (an older page already uses it): the address would be wrong, so say so.
			$r['errors'][] = "$label: WordPress saved the address as \"{$got->post_name}\" instead of \"{$it['slug']}\". Another page (maybe in the trash) uses that slug; delete it and run the import again.";
		}
		hscf_write_meta( $id, $it, true );
		$r[ $existed ? 'updated' : 'created' ][] = $label;
	}

	// Generated pages that are no longer in the manifest.
	$want = array_flip( array_map( function ( $i ) { return (string) $i['path']; }, $items ) );
	$all  = get_posts( array( 'post_type' => array( 'page', 'post', 'en_post' ), 'post_status' => array( 'publish', 'draft', 'private', 'pending' ),
		'numberposts' => -1, 'fields' => 'ids', 'meta_key' => '_hscf_path', 'no_found_rows' => true, 'suppress_filters' => true ) );
	foreach ( $all as $pid ) {
		$p = (string) get_post_meta( $pid, '_hscf_path', true );
		if ( isset( $want[ $p ] ) ) continue;
		if ( $prune ) { if ( ! $dry ) wp_trash_post( $pid ); $r['pruned'][] = '/' . $p; }
		else $r['orphans'][] = '/' . $p;
	}

	if ( ! $dry ) {
		update_option( 'hscf_partials', $m['partials'], true );
		hscf_save_static( $m['static'] );
		update_option( 'hscf_redirects', array_values( $m['redirects'] ), true );
		update_option( 'hscf_notfound', $m['notfound'] ?? null, false );
		$s = $m['settings'];
		foreach ( array( 'blogname', 'blogdescription', 'timezone_string' ) as $k ) {
			if ( isset( $s[ $k ] ) ) update_option( $k, $s[ $k ] );
		}
		if ( ! empty( $s['contact_to'] ) && is_email( $s['contact_to'] ) ) update_option( 'hscf_contact_to', $s['contact_to'], true );
		$home = $ids[''] ?? hscf_find_by_path( '' );
		if ( $home > 0 ) {
			update_option( 'show_on_front', 'page' );
			update_option( 'page_on_front', $home );
			update_option( 'page_for_posts', 0 );
		}
		update_option( 'default_comment_status', 'closed' );
		update_option( 'default_ping_status', 'closed' );
		if ( ! empty( $s['permalink_structure'] ) && get_option( 'permalink_structure' ) !== $s['permalink_structure'] ) {
			global $wp_rewrite;
			$wp_rewrite->set_permalink_structure( $s['permalink_structure'] );
		}
		flush_rewrite_rules( false );
		// Clear page caches so the new pages show right away (LiteSpeed Cache, WP Super Cache, W3TC, object cache).
		wp_cache_flush();
		do_action( 'litespeed_purge_all' );
		if ( function_exists( 'wp_cache_clear_cache' ) ) wp_cache_clear_cache();
		if ( function_exists( 'w3tc_flush_all' ) ) w3tc_flush_all();
		update_option( 'hscf_last_sync', array(
			'manifest_generated' => $m['generated'] ?? '', 'time' => current_time( 'mysql' ),
			'created' => count( $r['created'] ), 'updated' => count( $r['updated'] ), 'unchanged' => $r['unchanged'],
			'kept_wp_edits' => $r['kept_wp_edits'], 'errors' => $r['errors'],
		), false );
	}
	wp_defer_term_counting( false );
	return $r;
}

function hscf_write_meta( $id, array $it, $with_content ) {
	$meta = array(
		'_hscf_path' => $it['path'], '_hscf_lang' => $it['lang'], '_hscf_alt' => $it['alt'], '_hscf_active' => $it['active'],
		'_hscf_head' => $it['head'], '_hscf_splash' => $it['splash'], '_hscf_extra' => $it['extra'],
		'_hscf_article_id' => $it['article_id'] ?? '',
	);
	foreach ( $meta as $k => $v ) update_post_meta( $id, $k, wp_slash( (string) $v ) );
	if ( $with_content ) {
		update_post_meta( $id, '_hscf_hash', $it['hash'] );
		update_post_meta( $id, '_hscf_content_hash', hscf_content_hash( $id ) );
	}
}

/* ---------- REST: POST /wp-json/hscf/v1/sync ---------- */
add_action( 'rest_api_init', function () {
	register_rest_route( 'hscf/v1', '/sync', array(
		'methods' => 'POST',
		'permission_callback' => function () { return current_user_can( 'manage_options' ); },
		'callback' => function ( WP_REST_Request $req ) {
			$m = $req->get_json_params();
			if ( ! is_array( $m ) ) return new WP_Error( 'hscf_bad_manifest', 'Send the manifest as JSON (Content-Type: application/json).', array( 'status' => 400 ) );
			@set_time_limit( 300 );
			$r = hscf_sync( $m, array( 'dry' => (bool) $req->get_param( 'dry' ), 'force' => (bool) $req->get_param( 'force' ), 'prune' => (bool) $req->get_param( 'prune' ) ) );
			return new WP_REST_Response( $r, $r['errors'] ? 422 : 200 );
		},
	) );
	register_rest_route( 'hscf/v1', '/status', array(
		'methods' => 'GET',
		'permission_callback' => function () { return current_user_can( 'manage_options' ); },
		'callback' => function () { return array( 'theme' => HSCF_THEME_VERSION, 'last_sync' => get_option( 'hscf_last_sync' ) ); },
	) );
} );

/* ---------- WP-CLI: wp hscf sync / wp hscf status ---------- */
if ( defined( 'WP_CLI' ) && WP_CLI ) {
	WP_CLI::add_command( 'hscf sync', function ( $args, $assoc ) {
		$file = $args[0] ?? '';
		if ( ! is_readable( $file ) ) WP_CLI::error( "Can't read the manifest file: $file" );
		$m = json_decode( file_get_contents( $file ), true );
		if ( ! is_array( $m ) ) WP_CLI::error( 'The manifest is not valid JSON.' );
		$r = hscf_sync( $m, array( 'dry' => ! empty( $assoc['dry-run'] ), 'force' => ! empty( $assoc['force'] ), 'prune' => ! empty( $assoc['prune'] ) ) );
		$verb = $r['dry_run'] ? 'would be ' : '';
		WP_CLI::log( sprintf( '%s%d created, %s%d updated, %d unchanged.', $verb, count( $r['created'] ), $verb, count( $r['updated'] ), $r['unchanged'] ) );
		foreach ( array( 'created', 'updated' ) as $k ) if ( $r[ $k ] && count( $r[ $k ] ) <= 40 ) WP_CLI::log( "  $k: " . implode( ' ', $r[ $k ] ) );
		if ( $r['kept_wp_edits'] ) WP_CLI::warning( 'Edited in WordPress, text kept (use --force to overwrite): ' . implode( ' ', $r['kept_wp_edits'] ) );
		if ( $r['kept_trashed'] ) WP_CLI::warning( 'In the trash, left there (use --force to restore): ' . implode( ' ', $r['kept_trashed'] ) );
		if ( $r['orphans'] ) WP_CLI::warning( 'No longer in the site project (use --prune to trash them): ' . implode( ' ', $r['orphans'] ) );
		if ( $r['pruned'] ) WP_CLI::log( ( $r['dry_run'] ? 'Would trash: ' : 'Trashed: ' ) . implode( ' ', $r['pruned'] ) );
		if ( $r['errors'] ) { foreach ( $r['errors'] as $e ) WP_CLI::warning( $e ); WP_CLI::error( count( $r['errors'] ) . ' problem(s).' ); }
		WP_CLI::success( $r['dry_run'] ? 'Dry run only: nothing was changed.' : 'Import finished.' );
	}, array( 'shortdesc' => 'Import the HSCF site manifest (pages, posts, SEO files, redirects).',
		'synopsis' => array(
			array( 'type' => 'positional', 'name' => 'file', 'description' => 'Path to manifest.json' ),
			array( 'type' => 'flag', 'name' => 'dry-run', 'optional' => true ),
			array( 'type' => 'flag', 'name' => 'force', 'optional' => true ),
			array( 'type' => 'flag', 'name' => 'prune', 'optional' => true ),
		) ) );
	WP_CLI::add_command( 'hscf status', function () {
		WP_CLI::log( 'Theme ' . HSCF_THEME_VERSION );
		WP_CLI::log( wp_json_encode( get_option( 'hscf_last_sync' ), JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE ) );
	} );
}
