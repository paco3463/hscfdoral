<?php
/**
 * Page rendering. Imported pages and posts are printed exactly as the generator built them:
 * head (title, description, canonical, hreflang, Open Graph, JSON-LD) + shared header + main + footer + popup.
 * Pages someone adds by hand in WordPress get the same header, footer and styles around their content.
 */
if ( ! defined( 'ABSPATH' ) ) exit;

/** True for pages and posts the importer created (the Spanish home page's stored address is the empty string). */
function hscf_is_item( $id ) {
	return $id && metadata_exists( 'post', $id, '_hscf_path' );
}

function hscf_t( $text ) {
	return str_replace( '{{theme}}', get_template_directory_uri(), (string) $text );
}

function hscf_partial( $key ) {
	static $parts = null;
	if ( $parts === null ) $parts = (array) get_option( 'hscf_partials', array() );
	return isset( $parts[ $key ] ) ? hscf_t( $parts[ $key ] ) : '';
}

function hscf_header_html( $lang, $active, $alt ) {
	$h = hscf_partial( 'header_' . $lang . '_' . $active );
	if ( $h === '' ) $h = hscf_partial( 'header_' . $lang . '_' );
	return str_replace( '@@ALT@@', esc_url( home_url( '/' . ltrim( (string) $alt, '/' ) ) ), $h );
}

/** What the current request should show. */
function hscf_current() {
	if ( is_404() ) return array( 'kind' => 'notfound' );
	$post = get_queried_object();
	if ( is_front_page() && ! ( $post instanceof WP_Post ) ) {
		$post = get_post( (int) get_option( 'page_on_front' ) );
	}
	if ( $post instanceof WP_Post && ( is_singular() || is_front_page() ) ) {
		if ( hscf_is_item( $post->ID ) ) return array( 'kind' => 'item', 'post' => $post );
		return array( 'kind' => 'wp', 'post' => $post );
	}
	return array( 'kind' => 'notfound' );
}

function hscf_lang_of_path( $path ) {
	return ( $path === 'en' || strpos( $path, 'en/' ) === 0 ) ? 'en' : 'es';
}

function hscf_render( $ctx ) {
	if ( $ctx['kind'] === 'item' ) {
		$p    = $ctx['post'];
		$lang = get_post_meta( $p->ID, '_hscf_lang', true ) ?: 'es';
		$doc  = array(
			'lang'   => $lang,
			'head'   => get_post_meta( $p->ID, '_hscf_head', true ),
			'main'   => $p->post_content,
			'splash' => get_post_meta( $p->ID, '_hscf_splash', true ),
			'extra'  => get_post_meta( $p->ID, '_hscf_extra', true ),
			'active' => get_post_meta( $p->ID, '_hscf_active', true ),
			'alt'    => get_post_meta( $p->ID, '_hscf_alt', true ),
		);
	} elseif ( $ctx['kind'] === 'wp' ) {
		$doc = hscf_wp_doc( $ctx['post'] );
	} else {
		$nf = get_option( 'hscf_notfound' );
		status_header( 404 );
		nocache_headers();
		$doc = is_array( $nf ) ? array( 'lang' => $nf['lang'] ?? 'es', 'head' => $nf['head'], 'main' => $nf['main'],
			'splash' => '', 'extra' => '', 'active' => '', 'alt' => 'en/' )
			: hscf_simple_doc( 'es', 'Página no encontrada | HSCF', '', '<section class="nf"><div class="wrap"><h1>Página no encontrada</h1><p><a class="btn" href="' . esc_url( home_url( '/' ) ) . '">Inicio</a></p></div></section>', 'en/', 'noindex' );
	}
	hscf_print( $doc );
}

function hscf_print( $doc ) {
	header( 'Content-Type: text/html; charset=utf-8' );
	echo "<!DOCTYPE html>\n<html lang=\"" . esc_attr( $doc['lang'] ) . "\">\n<head>\n";
	echo hscf_t( $doc['head'] );
	wp_head();
	echo "</head>\n<body>\n";
	echo hscf_partial( 'svgdefs' ) . "\n";
	echo hscf_t( $doc['splash'] );
	if ( function_exists( 'wp_body_open' ) ) wp_body_open();
	echo hscf_header_html( $doc['lang'], $doc['active'], $doc['alt'] );
	echo "<main id=\"main\">\n" . hscf_t( $doc['main'] ) . "\n</main>\n";
	echo hscf_partial( 'footer_' . $doc['lang'] );
	echo hscf_partial( 'modal_' . $doc['lang'] );
	echo hscf_t( $doc['extra'] );
	echo '<script src="' . esc_url( get_template_directory_uri() . '/assets/js/main.js?v=' . HSCF_THEME_VERSION ) . '" defer></script>' . "\n";
	wp_footer();
	echo "</body>\n</html>\n";
}

/** A page or post created by hand in WordPress (not by the generator). */
function hscf_wp_doc( WP_Post $p ) {
	$path  = trim( (string) wp_make_link_relative( get_permalink( $p ) ), '/' );
	$lang  = hscf_lang_of_path( $path );
	$title = get_the_title( $p );
	$desc  = has_excerpt( $p ) ? get_the_excerpt( $p ) : wp_trim_words( wp_strip_all_tags( $p->post_content ), 25, '…' );
	setup_postdata( $p );
	$content = apply_filters( 'the_content', $p->post_content );
	wp_reset_postdata();
	$home  = $lang === 'en' ? home_url( '/en/' ) : home_url( '/' );
	$crumb = '<nav class="crumbs" aria-label="' . ( $lang === 'en' ? 'Breadcrumb' : 'Ruta de navegación' ) . '"><ol><li><a href="' . esc_url( $home ) . '">'
		. ( $lang === 'en' ? 'Home' : 'Inicio' ) . '</a></li><li><span aria-current="page">' . esc_html( $title ) . '</span></li></ol></nav>';
	$main  = '<section class="page-hero"><div class="wrap">' . $crumb . '<div class="page-hero-grid page-hero-grid--text"><div><h1>' . esc_html( $title )
		. '</h1></div></div></div></section><section class="section section--tight section--flush-top"><div class="wrap"><div class="prose">' . $content . '</div></div></section>';
	$robots = $p->post_status === 'publish' ? 'index, follow' : 'noindex';
	return hscf_simple_doc( $lang, $title . ' | HSCF', $desc, $main, $lang === 'en' ? '' : 'en/', $robots, get_permalink( $p ) );
}

function hscf_simple_doc( $lang, $title, $desc, $main, $alt, $robots = 'index, follow', $canonical = '' ) {
	$t    = get_template_directory_uri();
	$head = '<meta charset="utf-8">' . "\n"
		. '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">' . "\n"
		. '<title>' . esc_html( $title ) . '</title>' . "\n"
		. ( $desc ? '<meta name="description" content="' . esc_attr( $desc ) . '">' . "\n" : '' )
		. ( $canonical ? '<link rel="canonical" href="' . esc_url( $canonical ) . '">' . "\n" : '' )
		. '<meta name="robots" content="' . esc_attr( $robots ) . '">' . "\n"
		. '<meta name="theme-color" content="#FE4109">' . "\n"
		. '<link rel="icon" href="' . esc_url( $t . '/assets/img/favicon.ico' ) . '" sizes="any">' . "\n"
		. '<link rel="preload" href="' . esc_url( $t . '/assets/fonts/fraunces.woff2' ) . '" as="font" type="font/woff2" crossorigin>' . "\n"
		. '<link rel="preload" href="' . esc_url( $t . '/assets/fonts/figtree.woff2' ) . '" as="font" type="font/woff2" crossorigin>' . "\n"
		. '<link rel="stylesheet" href="' . esc_url( $t . '/assets/css/styles.css?v=' . HSCF_THEME_VERSION ) . '">' . "\n";
	return array( 'lang' => $lang, 'head' => $head, 'main' => $main, 'splash' => '', 'extra' => '', 'active' => '', 'alt' => $alt );
}

/* Imported pages hold hand-built HTML: open them in the code editor so WordPress doesn't rewrite the markup. */
add_filter( 'use_block_editor_for_post', function ( $use, $post ) {
	return ( $post && hscf_is_item( $post->ID ) ) ? false : $use;
}, 10, 2 );
add_filter( 'wp_default_editor', function ( $editor ) {
	global $post;
	return ( $post && hscf_is_item( $post->ID ) ) ? 'html' : $editor;
} );
add_filter( 'user_can_richedit', function ( $can ) {
	global $post;
	return ( $post && hscf_is_item( $post->ID ) ) ? false : $can;
} );
