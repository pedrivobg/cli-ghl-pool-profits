<?php
/**
 * Local test of bwb-ghl.php with WordPress/Elementor stubs: `php site/bluewater/test-bwb-ghl.php`.
 * Runs every hook path and checks the payload each GHL webhook receives (keys used by scripts/bw_forms.py).
 */

define( 'DAY_IN_SECONDS', 86400 );
$GLOBALS['hooks'] = array();
$GLOBALS['sent']  = array();
$GLOBALS['opts']  = array();

function add_action( $h, $cb ) { $GLOBALS['hooks'][ $h ] = $cb; }
function add_filter( $h, $cb ) { $GLOBALS['hooks'][ $h ] = $cb; }
function wp_parse_url( $u, $c = -1 ) { return parse_url( $u, $c ); }
function wp_json_encode( $d ) { return json_encode( $d ); }
function wp_unslash( $v ) { return stripslashes( $v ); }
function wp_get_raw_referer() { return 'https://bluewaterbrokerage.com/from-referer/'; }
function is_wp_error( $x ) { return $x instanceof WP_Error; }
function wp_remote_post( $url, $args ) { $GLOBALS['sent'][] = array( $url, json_decode( $args['body'], true ) ); return array( 'code' => 200 ); }
function wp_remote_retrieve_response_code( $r ) { return $r['code']; }
function get_option( $k, $d = false ) { return isset( $GLOBALS['opts'][ $k ] ) ? $GLOBALS['opts'][ $k ] : $d; }
function update_option( $k, $v, $a = null ) { $GLOBALS['opts'][ $k ] = $v; }
function get_transient( $k ) { return get_option( 't_' . $k ); }
function set_transient( $k, $v, $e ) { update_option( 't_' . $k, $v ); }
function current_user_can( $c ) { return false; }
function register_rest_route( $ns, $r, $a ) { $GLOBALS['routes'][ $ns . $r ] = $a; }
class WP_Error { function get_error_message() { return 'err'; } }
class WP_HTTP_Response { public $s; function __construct( $s ) { $this->s = $s; } function get_status() { return $this->s; } }
class Req {
	function __construct( $route, $body, $json = true ) { $this->r = $route; $this->b = $body; $this->j = $json; }
	function get_route() { return $this->r; }
	function get_json_params() { return $this->j ? json_decode( $this->b, true ) : null; }
	function get_body() { return $this->b; }
}
class Rec {
	function __construct( $id, $fields ) { $this->id = $id; $this->f = $fields; }
	function get( $k ) { return 'fields' === $k ? $this->f : null; }
	function get_form_settings( $k ) { return 'id' === $k ? $this->id : null; }
}
function fields( $a ) { $o = array(); foreach ( $a as $k => $v ) { $o[ $k ] = array( 'id' => $k, 'value' => $v ); } return $o; }

require __DIR__ . '/bwb-ghl.php';

$fail = 0;
function expect( $label, $hook, $want ) {
	global $fail;
	$got = array_pop( $GLOBALS['sent'] );
	$GLOBALS['sent'] = array();
	if ( null === $want ) {
		$ok = null === $got;
	} else {
		$ok = $got && strpos( $got[0], BWB_GHL::BASE . "__HOOK_{$hook}__" ) === 0 && $got[1] === $want;
	}
	echo ( $ok ? 'ok   ' : 'FAIL ' ) . $label . ( $ok ? '' : "\n     got: " . json_encode( $got ) . "\n     want: " . json_encode( $want ) ) . "\n";
	$fail += $ok ? 0 : 1;
}
$el   = $GLOBALS['hooks']['elementor_pro/forms/new_record'];
$rest = $GLOBALS['hooks']['rest_request_after_callbacks'];

$_POST['referrer'] = 'https://bluewaterbrokerage.com/resources/?utm_source=x';
call_user_func( $el, new Rec( 'bwr0009', fields( array( 'name' => '  Mary  Ann Smith ', 'email' => 'm@x.com', 'opinion' => 'on', 'hp' => '' ) ) ), null );
expect( 'seller guide, checked, 3-word name', 'SELLER', array( 'first_name' => 'Mary', 'last_name' => 'Ann Smith', 'email' => 'm@x.com', 'opinion' => 'yes', 'page' => '/resources/' ) );
call_user_func( $el, new Rec( 'bwr0010', fields( array( 'name' => 'Cher', 'email' => 'c@x.com', 'register' => '', 'hp' => '' ) ) ), null );
expect( 'buyer guide, unchecked, 1-word name', 'BUYER', array( 'first_name' => 'Cher', 'last_name' => '', 'email' => 'c@x.com', 'register' => 'no', 'page' => '/resources/' ) );
call_user_func( $el, new Rec( 'bwr0010', fields( array( 'name' => 'Bot', 'email' => 'b@x.com', 'register' => 'on', 'hp' => 'spam' ) ) ), null );
expect( 'honeypot filled -> nothing', 'BUYER', null );
$_POST['referrer'] = 'https://bluewaterbrokerage.com/contact/';
call_user_func( $el, new Rec( 'c6411dd', fields( array( 'name' => 'John Doe', 'email' => 'j@x.com', 'phone' => '(843) 555-0101', 'message' => "Hi\nBill" ) ) ), null );
expect( 'contact page form', 'CONTACT', array( 'first_name' => 'John', 'last_name' => 'Doe', 'email' => 'j@x.com', 'phone' => '(843) 555-0101', 'message' => "Hi\nBill", 'page' => '/contact/' ) );
unset( $_POST['referrer'] );
call_user_func( $el, new Rec( '59d31fac', fields( array( 'name' => '', 'email' => 'k@x.com', 'phone' => '', 'message' => '' ) ) ), null );
expect( 'home contact form, no name, referer fallback', 'CONTACT', array( 'first_name' => '', 'last_name' => '', 'email' => 'k@x.com', 'phone' => '', 'message' => '', 'page' => '/from-referer/' ) );
$_POST['referrer'] = 'https://bluewaterbrokerage.com/';
call_user_func( $el, new Rec( '36394603', fields( array( 'email' => 'n@x.com' ) ) ), null );
expect( 'footer newsletter', 'NEWSLETTER', array( 'email' => 'n@x.com', 'page' => '/' ) );
call_user_func( $el, new Rec( 'other123', fields( array( 'email' => 'o@x.com' ) ) ), null );
expect( 'unknown form -> nothing', 'CONTACT', null );

$who  = array( 'business' => 'Blue Pools', 'name' => 'Ann Lee', 'email' => 'a@x.com', 'phone' => '843-555-0102', 'city' => 'Myrtle Beach, SC', 'report' => true, 'talk' => false );
$gate = json_encode( array( 'type' => 'gate', 'who' => $who, 'figures' => null, 'website' => '', 'page' => '/route-calculator/' ) );
$r = call_user_func( $rest, 'RESP', null, new Req( '/bwb/v1/route-lead', $gate ) );
expect( 'calculator gate', 'GATE', array( 'first_name' => 'Ann', 'last_name' => 'Lee', 'email' => 'a@x.com', 'phone' => '843-555-0102', 'business' => 'Blue Pools', 'city' => 'Myrtle Beach, SC', 'report' => 'yes', 'talk' => 'no', 'page' => '/route-calculator/' ) );
echo ( 'RESP' === $r ? 'ok   ' : 'FAIL ' ) . "endpoint response passed through untouched\n";
$fail += 'RESP' === $r ? 0 : 1;
$fig  = array( 'monthly_billing' => 42000, 'visits_per_week' => 310.5, 'quality_score' => 6.42, 'multiple' => 10.2, 'value_low' => 410000, 'value_high' => 470000, 'equipment_value' => 85000, 'inventory_value' => 12000, 'is_franchise' => false, 'has_agreements' => 'Some signed' );
$figb = json_encode( array( 'type' => 'figures', 'who' => $who, 'figures' => $fig, 'website' => '', 'page' => '/route-calculator/' ) );
call_user_func( $rest, 'RESP', null, new Req( '/bwb/v1/route-lead', $figb, false ) ); // sendBeacon body
expect( 'calculator figures (beacon body)', 'FIGURES', array( 'first_name' => 'Ann', 'last_name' => 'Lee', 'email' => 'a@x.com', 'monthly_billing' => '42000', 'visits_per_week' => '310.5', 'quality_score' => '6.42', 'multiple' => '10.2', 'value_low' => '410000', 'value_high' => '470000', 'equipment_value' => '85000', 'inventory_value' => '12000', 'is_franchise' => 'no', 'agreements' => 'Some signed', 'page' => '/route-calculator/' ) );
call_user_func( $rest, 'RESP', null, new Req( '/bwb/v1/route-lead', $figb ) );
expect( 'same figures again -> nothing', 'FIGURES', null );
call_user_func( $rest, 'RESP', null, new Req( '/bwb/v1/route-lead', str_replace( '"website":""', '"website":"x"', $gate ) ) );
expect( 'calculator honeypot -> nothing', 'GATE', null );
call_user_func( $rest, new WP_HTTP_Response( 400 ), null, new Req( '/bwb/v1/route-lead', $gate ) );
expect( 'endpoint refused the lead -> nothing', 'GATE', null );
call_user_func( $rest, 'RESP', null, new Req( '/wp/v2/pages', $gate ) );
expect( 'other REST route -> nothing', 'GATE', null );
call_user_func( $rest, 'RESP', null, new Req( '/bwb/v1/route-lead', json_encode( array( 'type' => 'figures', 'who' => array( 'name' => 'X' ), 'figures' => $fig ) ) ) );
expect( 'figures without email -> nothing', 'FIGURES', null );

class KReq { function __construct( $k ) { $this->k = $k; } function get_param( $n ) { return 'key' === $n ? $this->k : null; } }
call_user_func( $GLOBALS['hooks']['rest_api_init'] );
$perm = $GLOBALS['routes']['bwb-ghl/v1/status']['permission_callback'];
$ok   = ! $perm( new KReq( 'wrong' ) ) && ! $perm( new KReq( '' ) ) && ! $perm( new KReq( '__KEY__' ) );
echo ( $ok ? 'ok   ' : 'FAIL ' ) . "test routes refuse a wrong/empty key (and the unfilled placeholder)\n";
$fail += $ok ? 0 : 1;
$log = get_option( 'bwb_ghl_log' );
$ok  = 7 === count( $log ) && 'figures' === $log[0][1] && 200 === $log[0][3]; // the 7 sends above, newest first
echo ( $ok ? 'ok   ' : 'FAIL ' ) . 'status log (' . count( $log ) . " entries)\n";
$fail += $ok ? 0 : 1;
echo $fail ? "\n$fail FAILED\n" : "\nall ok\n";
exit( $fail ? 1 : 0 );
