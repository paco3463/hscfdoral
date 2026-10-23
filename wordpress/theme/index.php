<?php
/**
 * Every front-end request renders through here: imported pages and posts use their stored parts,
 * anything else (a page added in WordPress, a 404) gets the same header, footer and styles.
 */
if ( ! defined( 'ABSPATH' ) ) exit;
hscf_render( hscf_current() );
