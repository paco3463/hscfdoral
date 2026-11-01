<?php
/**
 * Leads: a private client pool built from the website's contact form (and QR landing links).
 *
 * Stores the inquiry: name, email, phone, who the help is for, service of interest, preferred language,
 * how to contact them, the visitor's message, where they came from, and whether they agreed to receive
 * news by email. The form asks people not to include health details, but messages can still contain
 * them, so the list is for administrators only and leads can be deleted at any time.
 *
 * Admin: Dashboard widget "New leads" and the Leads screen (filters, status, notes, CSV export, delete),
 * administrators only. Table: {prefix}hscf_leads.
 */
if ( ! defined( 'ABSPATH' ) ) exit;

const HSCF_LEADS_DB_VERSION = '2';  // 2: message column

function hscf_leads_table() { global $wpdb; return $wpdb->prefix . 'hscf_leads'; }

function hscf_leads_statuses() {
	return array( 'new' => 'Nuevo', 'contacted' => 'Contactado', 'client' => 'Ya es cliente', 'not_fit' => 'No aplica' );
}

/* ---------- table ---------- */
function hscf_leads_install() {
	global $wpdb;
	require_once ABSPATH . 'wp-admin/includes/upgrade.php';
	$t = hscf_leads_table();
	$c = $wpdb->get_charset_collate();
	dbDelta( "CREATE TABLE $t (
		id bigint(20) unsigned NOT NULL AUTO_INCREMENT,
		created_at datetime NOT NULL,
		name varchar(120) NOT NULL DEFAULT '',
		email varchar(160) NOT NULL DEFAULT '',
		phone varchar(40) NOT NULL DEFAULT '',
		for_whom varchar(80) NOT NULL DEFAULT '',
		service varchar(120) NOT NULL DEFAULT '',
		language varchar(40) NOT NULL DEFAULT '',
		contact_by varchar(40) NOT NULL DEFAULT '',
		message text NULL,
		page_language varchar(2) NOT NULL DEFAULT 'es',
		source varchar(60) NOT NULL DEFAULT 'web',
		consent_marketing tinyint(1) NOT NULL DEFAULT 0,
		consent_at datetime NULL DEFAULT NULL,
		status varchar(20) NOT NULL DEFAULT 'new',
		notes text NULL,
		PRIMARY KEY  (id),
		KEY created_at (created_at),
		KEY status (status),
		KEY email (email)
	) $c;" );
	update_option( 'hscf_leads_db_version', HSCF_LEADS_DB_VERSION, false );
}
add_action( 'after_switch_theme', 'hscf_leads_install' );
add_action( 'admin_init', function () { if ( get_option( 'hscf_leads_db_version' ) !== HSCF_LEADS_DB_VERSION ) hscf_leads_install(); } );

/* ---------- saving (called by the contact form) ---------- */
function hscf_lead_store( array $d ) {
	global $wpdb;
	if ( get_option( 'hscf_leads_db_version' ) !== HSCF_LEADS_DB_VERSION ) hscf_leads_install();
	$now = current_time( 'mysql', true );
	$src = strtolower( preg_replace( '/[^a-z0-9\-]/i', '', (string) ( $d['source'] ?? '' ) ) );
	$row = array(
		'created_at'        => $now,
		'name'              => mb_substr( (string) ( $d['name'] ?? '' ), 0, 120 ),
		'email'             => mb_substr( (string) ( $d['email'] ?? '' ), 0, 160 ),
		'phone'             => mb_substr( (string) ( $d['phone'] ?? '' ), 0, 40 ),
		'for_whom'          => mb_substr( (string) ( $d['for'] ?? '' ), 0, 80 ),
		'service'           => mb_substr( (string) ( $d['service'] ?? '' ), 0, 120 ),
		'language'          => mb_substr( (string) ( $d['language'] ?? '' ), 0, 40 ),
		'contact_by'        => mb_substr( (string) ( $d['contact_by'] ?? '' ), 0, 40 ),
		'message'           => mb_substr( (string) ( $d['message'] ?? '' ), 0, 3000 ),
		'page_language'     => ( $d['page_language'] ?? '' ) === 'en' ? 'en' : 'es',
		'source'            => $src !== '' ? mb_substr( $src, 0, 60 ) : 'web',
		'consent_marketing' => ! empty( $d['consent'] ) ? 1 : 0,
		'consent_at'        => ! empty( $d['consent'] ) ? $now : null,
		'status'            => 'new',
	);
	return $wpdb->insert( hscf_leads_table(), $row ) ? (int) $wpdb->insert_id : 0;
}

/* ---------- queries ---------- */
function hscf_leads_query( $args = array() ) {
	global $wpdb; $t = hscf_leads_table();
	$where = array( '1=1' ); $vals = array();
	if ( ! empty( $args['status'] ) && isset( hscf_leads_statuses()[ $args['status'] ] ) ) { $where[] = 'status = %s'; $vals[] = $args['status']; }
	if ( isset( $args['consent'] ) && $args['consent'] !== '' ) { $where[] = 'consent_marketing = %d'; $vals[] = (int) $args['consent']; }
	if ( ! empty( $args['source'] ) ) { $where[] = 'source = %s'; $vals[] = $args['source']; }
	if ( ! empty( $args['q'] ) ) { $like = '%' . $wpdb->esc_like( $args['q'] ) . '%'; $where[] = '(name LIKE %s OR email LIKE %s OR phone LIKE %s)'; array_push( $vals, $like, $like, $like ); }
	$limit = isset( $args['limit'] ) ? max( 1, (int) $args['limit'] ) : 50;
	$offset = isset( $args['offset'] ) ? max( 0, (int) $args['offset'] ) : 0;
	$sql = "SELECT * FROM $t WHERE " . implode( ' AND ', $where ) . ' ORDER BY created_at DESC';
	$count_sql = "SELECT COUNT(*) FROM $t WHERE " . implode( ' AND ', $where );
	$total = (int) ( $vals ? $wpdb->get_var( $wpdb->prepare( $count_sql, $vals ) ) : $wpdb->get_var( $count_sql ) );
	if ( $limit < PHP_INT_MAX ) $sql .= $wpdb->prepare( ' LIMIT %d OFFSET %d', $limit, $offset );
	$rows = $vals ? $wpdb->get_results( $wpdb->prepare( $sql, $vals ) ) : $wpdb->get_results( $sql );
	return array( $rows ?: array(), $total );
}
function hscf_leads_count_since( $days ) {
	global $wpdb;
	return (int) $wpdb->get_var( $wpdb->prepare( 'SELECT COUNT(*) FROM ' . hscf_leads_table() . ' WHERE created_at >= %s', gmdate( 'Y-m-d H:i:s', time() - $days * DAY_IN_SECONDS ) ) );
}
function hscf_leads_group( $col, $days = 90 ) {
	global $wpdb;
	if ( ! in_array( $col, array( 'source', 'service', 'status', 'page_language' ), true ) ) return array();
	return $wpdb->get_results( $wpdb->prepare( "SELECT $col AS k, COUNT(*) AS n FROM " . hscf_leads_table() . " WHERE created_at >= %s GROUP BY $col ORDER BY n DESC LIMIT 6", gmdate( 'Y-m-d H:i:s', time() - $days * DAY_IN_SECONDS ) ) );
}
function hscf_lead_local( $utc ) { return $utc ? get_date_from_gmt( $utc, 'M j, Y · g:i a' ) : ''; }

/* ---------- admin: shared styles ---------- */
function hscf_leads_admin_css() { ?>
<style>
.hscf-l { --e:#C93203; --c:#3A2219; --d:#7D6156; --b:#FFEDE2; --m:#FFFBF7; }
.hscf-l .kpis{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;margin:0 0 12px}
.hscf-l .kpi{background:var(--m);border:1px solid #eadfd8;border-radius:10px;padding:10px 12px}
.hscf-l .kpi b{display:block;font-size:22px;line-height:1.1;color:var(--c)} .hscf-l .kpi span{font-size:11px;color:var(--d);text-transform:uppercase;letter-spacing:.06em}
.hscf-l .pill{display:inline-block;font-size:11px;font-weight:600;padding:1px 8px;border-radius:999px;background:#f0ebe8;color:var(--c)}
.hscf-l .pill.new{background:var(--b);color:var(--e)} .hscf-l .pill.contacted{background:#e8f0fb;color:#1d4f91} .hscf-l .pill.client{background:#e7f4ea;color:#1f5a2e} .hscf-l .pill.not_fit{background:#eee;color:#555}
.hscf-l .ok{color:#1f5a2e;font-weight:600} .hscf-l .muted{color:var(--d)}
.hscf-l ul.recent{margin:0} .hscf-l ul.recent li{display:flex;justify-content:space-between;gap:8px;border-top:1px solid #f0e8e3;padding:7px 0;margin:0}
.hscf-l .chips{display:flex;flex-wrap:wrap;gap:6px;margin:8px 0 0} .hscf-l .chips span{background:#f7f2ef;border-radius:999px;padding:2px 9px;font-size:12px}
.hscf-l table.widefat td{vertical-align:top} .hscf-l textarea{width:100%;min-height:38px}
</style>
<?php }

/* ---------- admin: dashboard widget ---------- */
add_action( 'wp_dashboard_setup', function () {
	if ( ! current_user_can( 'manage_options' ) ) return;
	wp_add_dashboard_widget( 'hscf_leads_widget', 'Nuevos contactos (leads)', 'hscf_leads_widget' );
	global $wp_meta_boxes; // keep it at the top
	$w = $wp_meta_boxes['dashboard']['normal']['core']['hscf_leads_widget'] ?? null;
	if ( $w ) { unset( $wp_meta_boxes['dashboard']['normal']['core']['hscf_leads_widget'] ); $wp_meta_boxes['dashboard']['normal']['high']['hscf_leads_widget'] = $w; }
} );
function hscf_leads_widget() {
	if ( get_option( 'hscf_leads_db_version' ) !== HSCF_LEADS_DB_VERSION ) hscf_leads_install();
	list( $rows ) = hscf_leads_query( array( 'limit' => 6 ) );
	list( , $new_total ) = hscf_leads_query( array( 'status' => 'new', 'limit' => 1 ) );
	list( , $opt_in ) = hscf_leads_query( array( 'consent' => 1, 'limit' => 1 ) );
	$st = hscf_leads_statuses();
	hscf_leads_admin_css(); ?>
	<div class="hscf-l">
		<div class="kpis">
			<div class="kpi"><b><?php echo (int) hscf_leads_count_since( 7 ); ?></b><span>Últimos 7 días</span></div>
			<div class="kpi"><b><?php echo (int) $new_total; ?></b><span>Por contactar</span></div>
			<div class="kpi"><b><?php echo (int) $opt_in; ?></b><span>Aceptan emails</span></div>
		</div>
		<?php if ( ! $rows ) : ?>
			<p class="muted">Todavía no hay contactos. Cuando alguien envíe el formulario de <a href="<?php echo esc_url( home_url( '/contacto/' ) ); ?>" target="_blank">/contacto/</a>, aparecerá aquí.</p>
		<?php else : ?>
			<ul class="recent">
			<?php foreach ( $rows as $r ) : ?>
				<li><span><strong><?php echo esc_html( $r->name ); ?></strong><br><span class="muted"><?php echo esc_html( $r->service ?: '—' ); ?> · <?php echo esc_html( $r->source ); ?></span></span>
				<span style="text-align:right"><span class="pill <?php echo esc_attr( $r->status ); ?>"><?php echo esc_html( $st[ $r->status ] ?? $r->status ); ?></span><br><span class="muted"><?php echo esc_html( hscf_lead_local( $r->created_at ) ); ?></span></span></li>
			<?php endforeach; ?>
			</ul>
		<?php endif;
		$src = hscf_leads_group( 'source' );
		if ( $src ) { echo '<p class="muted" style="margin:10px 0 0">Origen (90 días)</p><div class="chips">'; foreach ( $src as $g ) echo '<span>' . esc_html( $g->k ) . ' · ' . (int) $g->n . '</span>'; echo '</div>'; } ?>
		<p style="margin:12px 0 0"><a class="button button-primary" href="<?php echo esc_url( admin_url( 'admin.php?page=hscf-leads' ) ); ?>">Ver todos los contactos</a></p>
	</div>
<?php }

/* ---------- admin: Leads screen ---------- */
add_action( 'admin_menu', function () {
	add_menu_page( 'Contactos', 'Contactos', 'manage_options', 'hscf-leads', 'hscf_leads_page', 'dashicons-groups', 3 );
} );

add_action( 'admin_post_hscf_leads_update', function () {
	if ( ! current_user_can( 'manage_options' ) ) wp_die( 'No permission.' );
	check_admin_referer( 'hscf_leads_update' );
	global $wpdb; $id = (int) ( $_POST['id'] ?? 0 );
	if ( $id ) {
		if ( ! empty( $_POST['delete'] ) ) $wpdb->delete( hscf_leads_table(), array( 'id' => $id ), array( '%d' ) );
		else {
			$status = sanitize_key( $_POST['status'] ?? 'new' ); if ( ! isset( hscf_leads_statuses()[ $status ] ) ) $status = 'new';
			$wpdb->update( hscf_leads_table(), array( 'status' => $status, 'notes' => sanitize_textarea_field( wp_unslash( $_POST['notes'] ?? '' ) ) ), array( 'id' => $id ), array( '%s', '%s' ), array( '%d' ) );
		}
	}
	wp_safe_redirect( wp_get_referer() ?: admin_url( 'admin.php?page=hscf-leads' ) ); exit;
} );

add_action( 'admin_post_hscf_leads_export', function () {
	if ( ! current_user_can( 'manage_options' ) ) wp_die( 'No permission.' );
	check_admin_referer( 'hscf_leads_export' );
	$args = array( 'status' => sanitize_key( $_GET['status'] ?? '' ), 'consent' => isset( $_GET['consent'] ) ? sanitize_text_field( wp_unslash( $_GET['consent'] ) ) : '', 'source' => sanitize_key( $_GET['source'] ?? '' ), 'limit' => PHP_INT_MAX );
	list( $rows ) = hscf_leads_query( $args );
	nocache_headers();
	header( 'Content-Type: text/csv; charset=utf-8' );
	header( 'Content-Disposition: attachment; filename=hscf-contactos-' . gmdate( 'Y-m-d' ) . '.csv' );
	$out = fopen( 'php://output', 'w' ); fwrite( $out, "\xEF\xBB\xBF" ); // UTF-8 BOM so Excel shows accents
	fputcsv( $out, array( 'Fecha', 'Nombre', 'Email', 'Teléfono', 'Para', 'Servicio', 'Idioma', 'Contactar por', 'Mensaje', 'Página', 'Origen', 'Acepta emails', 'Estado', 'Notas' ) );
	$st = hscf_leads_statuses();
	$safe = function ( $v ) { $v = (string) $v; return ( $v !== '' && strpbrk( $v[0], '=+-@' ) !== false ) ? "'" . $v : $v; }; // no spreadsheet formulas
	foreach ( $rows as $r ) fputcsv( $out, array_map( $safe, array( hscf_lead_local( $r->created_at ), $r->name, $r->email, $r->phone, $r->for_whom, $r->service, $r->language, $r->contact_by, $r->message, $r->page_language, $r->source, $r->consent_marketing ? 'Sí' : 'No', $st[ $r->status ] ?? $r->status, $r->notes ) ) );
	fclose( $out ); exit;
} );

function hscf_leads_page() {
	if ( ! current_user_can( 'manage_options' ) ) return;
	if ( get_option( 'hscf_leads_db_version' ) !== HSCF_LEADS_DB_VERSION ) hscf_leads_install();
	$f = array( 'status' => sanitize_key( $_GET['status'] ?? '' ), 'consent' => isset( $_GET['consent'] ) ? sanitize_text_field( wp_unslash( $_GET['consent'] ) ) : '', 'source' => sanitize_key( $_GET['source'] ?? '' ), 'q' => sanitize_text_field( wp_unslash( $_GET['q'] ?? '' ) ) );
	$paged = max( 1, (int) ( $_GET['paged'] ?? 1 ) ); $per = 50;
	list( $rows, $total ) = hscf_leads_query( $f + array( 'limit' => $per, 'offset' => ( $paged - 1 ) * $per ) );
	$st = hscf_leads_statuses();
	$export = wp_nonce_url( add_query_arg( array_filter( array( 'action' => 'hscf_leads_export', 'status' => $f['status'], 'consent' => $f['consent'], 'source' => $f['source'] ), 'strlen' ), admin_url( 'admin-post.php' ) ), 'hscf_leads_export' );
	hscf_leads_admin_css(); ?>
	<div class="wrap hscf-l">
		<h1 class="wp-heading-inline">Contactos</h1>
		<a class="page-title-action" href="<?php echo esc_url( $export ); ?>">Exportar CSV (filtro actual)</a>
		<p class="muted">Personas que escribieron por el sitio web. Los mensajes pueden incluir información personal o de salud: no los compartas fuera de la práctica. Para campañas de email, usa solo quienes <strong>aceptan emails</strong>.</p>
		<div class="kpis" style="max-width:640px">
			<div class="kpi"><b><?php echo (int) hscf_leads_count_since( 30 ); ?></b><span>Últimos 30 días</span></div>
			<div class="kpi"><b><?php echo (int) hscf_leads_query( array( 'status' => 'new', 'limit' => 1 ) )[1]; ?></b><span>Por contactar</span></div>
			<div class="kpi"><b><?php echo (int) hscf_leads_query( array( 'status' => 'client', 'limit' => 1 ) )[1]; ?></b><span>Ya son clientes</span></div>
		</div>
		<form method="get" style="display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:6px 0 12px">
			<input type="hidden" name="page" value="hscf-leads">
			<input type="search" name="q" value="<?php echo esc_attr( $f['q'] ); ?>" placeholder="Nombre, email o teléfono">
			<select name="status"><option value="">Todos los estados</option><?php foreach ( $st as $k => $v ) printf( '<option value="%s"%s>%s</option>', esc_attr( $k ), selected( $f['status'], $k, false ), esc_html( $v ) ); ?></select>
			<select name="consent"><option value="">Emails: todos</option><option value="1"<?php selected( $f['consent'], '1' ); ?>>Aceptan emails</option><option value="0"<?php selected( $f['consent'], '0' ); ?>>No aceptan</option></select>
			<input type="text" name="source" value="<?php echo esc_attr( $f['source'] ); ?>" placeholder="Origen (ej. qr-sala-de-espera)">
			<button class="button">Filtrar</button>
		</form>
		<table class="widefat striped">
			<thead><tr><th>Fecha</th><th>Contacto</th><th>Interés</th><th style="width:24%">Mensaje</th><th>Origen</th><th>Emails</th><th style="width:26%">Estado y notas</th></tr></thead>
			<tbody>
			<?php if ( ! $rows ) echo '<tr><td colspan="7" class="muted">No hay contactos con este filtro.</td></tr>';
			foreach ( $rows as $r ) : ?>
				<tr>
					<td><?php echo esc_html( hscf_lead_local( $r->created_at ) ); ?></td>
					<td><strong><?php echo esc_html( $r->name ); ?></strong><br>
						<?php if ( $r->email ) echo '<a href="mailto:' . esc_attr( $r->email ) . '">' . esc_html( $r->email ) . '</a><br>'; ?>
						<?php if ( $r->phone ) echo '<a href="tel:' . esc_attr( preg_replace( '/[^0-9+]/', '', $r->phone ) ) . '">' . esc_html( $r->phone ) . '</a>'; ?>
						<div class="muted"><?php echo esc_html( trim( $r->language . ( $r->contact_by ? ' · ' . $r->contact_by : '' ), ' ·' ) ); ?></div></td>
					<td><?php echo esc_html( $r->service ?: '—' ); ?><div class="muted"><?php echo esc_html( $r->for_whom ); ?></div></td>
					<td><?php if ( $r->message === null || $r->message === '' ) { echo '<span class="muted">—</span>'; } else { $m = (string) $r->message;
						echo mb_strlen( $m ) > 160 ? '<details><summary>' . esc_html( mb_substr( $m, 0, 160 ) ) . '…</summary><div style="white-space:pre-wrap">' . esc_html( $m ) . '</div></details>' : '<div style="white-space:pre-wrap">' . esc_html( $m ) . '</div>'; } ?></td>
					<td><?php echo esc_html( $r->source ); ?><div class="muted"><?php echo $r->page_language === 'en' ? 'English' : 'Español'; ?></div></td>
					<td><?php echo $r->consent_marketing ? '<span class="ok">Sí</span>' : '<span class="muted">No</span>'; ?></td>
					<td><form method="post" action="<?php echo esc_url( admin_url( 'admin-post.php' ) ); ?>">
						<?php wp_nonce_field( 'hscf_leads_update' ); ?><input type="hidden" name="action" value="hscf_leads_update"><input type="hidden" name="id" value="<?php echo (int) $r->id; ?>">
						<select name="status"><?php foreach ( $st as $k => $v ) printf( '<option value="%s"%s>%s</option>', esc_attr( $k ), selected( $r->status, $k, false ), esc_html( $v ) ); ?></select>
						<textarea name="notes" placeholder="Notas internas (sin detalles de salud)"><?php echo esc_textarea( $r->notes ); ?></textarea>
						<button class="button button-small">Guardar</button>
						<button class="button button-small button-link-delete" name="delete" value="1" onclick="return confirm('¿Eliminar este contacto definitivamente?')">Eliminar</button>
					</form></td>
				</tr>
			<?php endforeach; ?>
			</tbody>
		</table>
		<?php $pages = (int) ceil( $total / $per ); if ( $pages > 1 ) echo '<div class="tablenav"><div class="tablenav-pages">' . paginate_links( array( 'base' => add_query_arg( 'paged', '%#%' ), 'format' => '', 'current' => $paged, 'total' => $pages ) ) . '</div></div>'; ?>
		<p class="muted"><?php echo (int) $total; ?> contacto(s).</p>
	</div>
<?php }
