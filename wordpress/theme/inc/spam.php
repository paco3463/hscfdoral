<?php
/**
 * Contact-form spam check. Nothing is thrown away: a request that looks like spam is saved in
 * Contactos with status "spam" and a note saying why, and no email is sent. The visitor sees the
 * normal "sent" message, so bots learn nothing.
 *
 * Rules (any one is enough):
 *  1. an answer the form doesn't offer (bots post their own values, e.g. "Telefono" without the accent);
 *     the allowed answers come from assets/form-options.json, written by build/build.py from the form itself
 *  2. sent less than 3 seconds after the page opened, or without the page's script (no _t field)
 *  3. Cyrillic, Chinese, Arabic, Korean or Thai script
 *  4. 3+ links, bulk-mail text ("unsubscribe"), a sales pitch (2+ sales phrases and more sales than care wording),
 *     or a scrambled one-word name (10+ letters, 2+ inner capitals, e.g. "kJhgfDsaqWer")
 */
if ( ! defined( 'ABSPATH' ) ) exit;

const HSCF_MIN_FILL_MS = 3000;

function hscf_form_options() {
	static $o = null;
	if ( $o === null ) {
		$p = get_theme_file_path( 'assets/form-options.json' );
		$o = is_readable( $p ) ? json_decode( (string) file_get_contents( $p ), true ) : array();
		if ( ! is_array( $o ) ) $o = array();
	}
	return $o;
}

/**
 * @param array    $d       for, service, language, contact_by, name, message
 * @param int|null $elapsed ms between page load and submit (-1 = missing); null skips the time rule (old requests)
 * @return string  the reason, in Spanish for the Contactos screen, or '' when it looks like a real person
 */
function hscf_spam_reason( array $d, $elapsed = null ) {
	$opts = hscf_form_options();
	foreach ( array( 'for' => 'para quién', 'service' => 'servicio', 'language' => 'idioma', 'contact_by' => 'contacto' ) as $k => $label ) {
		$v = (string) ( $d[ $k ] ?? '' );
		if ( $v !== '' && ! empty( $opts[ $k ] ) && ! in_array( $v, $opts[ $k ], true ) ) return "respuesta que el formulario no ofrece ($label)";
	}
	if ( $elapsed !== null && $elapsed < HSCF_MIN_FILL_MS ) return $elapsed < 0 ? 'enviado sin pasar por la página' : 'enviado demasiado rápido';

	$name = (string) ( $d['name'] ?? '' ); $msg = (string) ( $d['message'] ?? '' );
	if ( preg_match( '/[\p{Cyrillic}\p{Han}\p{Arabic}\p{Hangul}\p{Thai}]/u', $name . ' ' . $msg ) ) return 'escritura no latina';
	if ( preg_match_all( '#https?://|www\.#i', $msg ) >= 3 ) return 'muchos enlaces';
	if ( preg_match( '/\b(unsubscribe|opt[ -]?out|darse de baja|cancelar (la )?suscripci)/iu', $msg ) ) return 'texto de email masivo';
	if ( preg_match( '/^\p{L}{10,}$/u', $name ) && preg_match_all( '/\p{Ll}\p{Lu}/u', $name ) >= 2 ) return 'nombre aleatorio';

	$sales = preg_match_all( '/\b(your (website|business|practice|clinic|site)|su (sitio|negocio|página|pagina|clínica|clinica)|seo|software|platform|plataforma|we offer|ofrecemos|our (team|company|agency)|nuestra (empresa|agencia)|free (trial|audit)|demo|partnership|marketing|growth|leads|ventas|sales|credentialing|billing services?)\b/iu', $msg );
	$care  = preg_match_all( '/\b(my (son|daughter|child|kid|husband|wife|partner)|mi (hijo|hija|niño|niña|esposo|esposa|pareja)|anxiety|ansiedad|depres\w*|autis\w*|appointment|cita|insurance|seguro|evaluat\w*|evaluaci\w*|therap\w*|terapia|diagnos\w*)\b/iu', $msg );
	if ( $sales >= 2 && $sales > $care ) return 'parece publicidad o venta';
	return '';
}
