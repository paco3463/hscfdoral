<?php
/**
 * Contact form: POST /wp-json/hscf/v1/contact (the form on /contacto/ and /en/contact/).
 *
 * Sends one email to the practice (option hscf_contact_to, default info@hscfdoral.com) with the visitor's
 * address as Reply-To. Nothing is stored in WordPress, logged or sent anywhere else: people sometimes
 * write about their health even when asked not to. Delivery needs WP Mail SMTP (see INSTALL.md).
 */
if ( ! defined( 'ABSPATH' ) ) exit;

add_action( 'rest_api_init', function () {
	register_rest_route( 'hscf/v1', '/contact', array(
		'methods' => 'POST',
		'permission_callback' => '__return_true',
		'callback' => 'hscf_contact_submit',
	) );
} );

function hscf_contact_submit( WP_REST_Request $req ) {
	$f = function ( $k, $max = 200 ) use ( $req ) {
		$v = $req->get_param( $k );
		$v = is_string( $v ) ? trim( wp_strip_all_tags( $v ) ) : '';
		return function_exists( 'mb_substr' ) ? mb_substr( $v, 0, $max ) : substr( $v, 0, $max );
	};
	if ( $f( '_gotcha' ) !== '' ) return new WP_REST_Response( array( 'ok' => true ), 200 );   // spam trap: pretend it worked

	$ip_key = 'hscf_cf_' . md5( ( $_SERVER['REMOTE_ADDR'] ?? '' ) . wp_salt( 'nonce' ) );
	$count  = (int) get_transient( $ip_key );
	if ( $count >= 5 ) return new WP_REST_Response( array( 'ok' => false, 'error' => 'too_many' ), 429 );

	$name  = $f( 'name', 120 );
	$email = sanitize_email( $f( 'email', 160 ) );
	$phone = preg_replace( '/[^0-9+()\-\s.]/', '', $f( 'phone', 40 ) );
	if ( $name === '' || ( $email === '' && trim( $phone ) === '' ) || ( $f( 'email' ) !== '' && ! is_email( $email ) ) ) {
		return new WP_REST_Response( array( 'ok' => false, 'error' => 'required' ), 400 );
	}
	$lang = $f( 'page_language', 2 ) === 'en' ? 'en' : 'es';
	$rows = array(
		( $lang === 'en' ? 'Name' : 'Nombre' )                    => $name,
		'Email'                                                   => $email,
		( $lang === 'en' ? 'Phone' : 'Teléfono' )                 => $phone,
		( $lang === 'en' ? 'For' : 'Para' )                       => $f( 'for' ),
		( $lang === 'en' ? 'Service' : 'Servicio' )               => $f( 'service' ),
		( $lang === 'en' ? 'Preferred language' : 'Idioma' )      => $f( 'language' ),
		( $lang === 'en' ? 'Contact by' : 'Contactar por' )       => $f( 'contact_by' ),
		( $lang === 'en' ? 'Message' : 'Mensaje' )                => $f( 'message', 3000 ),
	);
	$body = '';
	foreach ( $rows as $k => $v ) if ( $v !== '' ) $body .= $k . ': ' . $v . "\n";
	$body .= "\n— " . ( $lang === 'en' ? 'Sent from the contact form on hscfdoral.com (English page).' : 'Enviado desde el formulario de contacto de hscfdoral.com.' ) . "\n";

	$to      = get_option( 'hscf_contact_to', 'info@hscfdoral.com' );
	$subject = ( $lang === 'en' ? 'New request from the website: ' : 'Nueva solicitud desde la web: ' ) . $name;
	$headers = array( 'Content-Type: text/plain; charset=UTF-8' );
	if ( $email ) $headers[] = 'Reply-To: ' . str_replace( array( "\r", "\n", '<', '>' ), '', $name ) . ' <' . $email . '>';

	set_transient( $ip_key, $count + 1, HOUR_IN_SECONDS );
	$sent = wp_mail( $to, $subject, $body, $headers );
	return new WP_REST_Response( array( 'ok' => (bool) $sent ), $sent ? 200 : 502 );
}
