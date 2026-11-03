<?php
/**
 * Local test of ps-ghl.php with WordPress stubs: `php site/poolshack/test-ps-ghl.php`.
 * Runs the WPForms hook with each form's real field layout and checks the payload each GHL webhook receives
 * (keys used by scripts/ps_site.py), plus the test route's guard against live webhooks.
 */

$GLOBALS['hooks'] = array();
$GLOBALS['sent']  = array();
$GLOBALS['opts']  = array();

function add_action( $h, $cb ) { $GLOBALS['hooks'][ $h ] = $cb; }
function wp_parse_url( $u, $c = -1 ) { return parse_url( $u, $c ); }
function wp_json_encode( $d ) { return json_encode( $d ); }
function wp_unslash( $v ) { return stripslashes( $v ); }
function wp_get_raw_referer() { return 'https://thepoolshackarizona.com/from-referer/'; }
function is_wp_error( $x ) { return $x instanceof WP_Error; }
function wp_remote_post( $url, $args ) { $GLOBALS['sent'][] = array( $url, json_decode( $args['body'], true ) ); return array( 'code' => 200 ); }
function wp_remote_retrieve_response_code( $r ) { return $r['code']; }
function get_option( $k, $d = false ) { return isset( $GLOBALS['opts'][ $k ] ) ? $GLOBALS['opts'][ $k ] : $d; }
function update_option( $k, $v, $a = null ) { $GLOBALS['opts'][ $k ] = $v; }
function current_user_can( $c ) { return false; }
function register_rest_route( $ns, $r, $a ) { $GLOBALS['routes'][ $ns . $r ] = $a; }
class WP_Error { function __construct( $c = '', $m = '', $d = null ) { $this->c = $c; } function get_error_message() { return 'err'; } }
class KReq {
	function __construct( $k, $json = null ) { $this->k = $k; $this->j = $json; }
	function get_param( $n ) { return 'key' === $n ? $this->k : null; }
	function get_json_params() { return $this->j; }
}

require __DIR__ . '/ps-ghl.php';

$fail = 0;
function check( $label, $ok, $extra = '' ) {
	global $fail;
	echo ( $ok ? 'ok   ' : 'FAIL ' ) . $label . ( $ok ? '' : "\n     " . $extra ) . "\n";
	$fail += $ok ? 0 : 1;
}
function expect( $label, $hook, $want ) {
	$got = array_pop( $GLOBALS['sent'] );
	$GLOBALS['sent'] = array();
	$ok  = null === $want ? null === $got : ( $got && PS_GHL::BASE . $hook === $got[0] && $got[1] === $want );
	check( $label, $ok, 'got: ' . json_encode( $got ) . "\n     want: " . json_encode( $want ) );
}
// WPForms passes $fields as id => array( name, value, id, type, … ).
function wpf( $a ) { $o = array(); foreach ( $a as $k => $v ) { $o[ $k ] = is_array( $v ) ? $v + array( 'id' => $k ) : array( 'id' => $k, 'name' => "f$k", 'value' => $v ); } return $o; }
$sub = $GLOBALS['hooks']['wpforms_process_complete'];

$_POST['page_url'] = 'https://thepoolshackarizona.com/?utm_source=google';
call_user_func( $sub, wpf( array( 1 => '  Mary  Ann Smith ', 2 => '(480) 555-0140', 3 => 'Yes', 4 => 'Weekly Pool Service' ) ), array(), array( 'id' => 440 ), 0 );
expect( '440 Request a Quote, 3-word name, US phone', '__HOOK_QUOTE__', array( 'first_name' => 'Mary', 'last_name' => 'Ann Smith', 'phone' => '+14805550140', 'new_customer' => 'Yes', 'service' => 'Weekly Pool Service', 'page' => '/' ) );

$_POST['page_url'] = 'https://thepoolshackarizona.com/contact/';
call_user_func( $sub, wpf( array( 1 => 'John Doe', 2 => '(602) 555-0143', 3 => 'John@X.com ', 4 => '1 Main St, Scottsdale', 5 => '85251', 6 => 'Equipment Repair', 7 => "Pump noise\nsince Monday", 8 => 'By checking this box…' ) ), array(), array( 'id' => '443' ), 12 );
expect( '443 Main Contact, all fields (consent not sent)', '__HOOK_CONTACT__', array( 'first_name' => 'John', 'last_name' => 'Doe', 'phone' => '+16025550143', 'email' => 'john@x.com', 'address' => '1 Main St, Scottsdale', 'postal_code' => '85251', 'service' => 'Equipment Repair', 'message' => "Pump noise\nsince Monday", 'page' => '/contact/' ) );

unset( $_POST['page_url'] );
call_user_func( $sub, wpf( array( 1 => array( 'value' => 'Ann Lee', 'first' => 'Ann', 'middle' => '', 'last' => 'Lee' ), 2 => '+1 480 555 0199', 3 => 'a@x.com', 4 => '', 5 => '85001', 6 => 'Other', 7 => '' ) ), array(), array( 'id' => 443 ), 0 );
expect( '443 first/last name format, optional fields empty, referer fallback', '__HOOK_CONTACT__', array( 'first_name' => 'Ann', 'last_name' => 'Lee', 'phone' => '+14805550199', 'email' => 'a@x.com', 'address' => '', 'postal_code' => '85001', 'service' => 'Other', 'message' => '', 'page' => '/from-referer/' ) );

call_user_func( $sub, wpf( array( 1 => 'Cher', 2 => '+44 20 7946 0000', 3 => 'No', 4 => 'Acid Wash' ) ), array(), array( 'id' => 440 ), 0 );
expect( '440 1-word name, foreign phone kept as typed', '__HOOK_QUOTE__', array( 'first_name' => 'Cher', 'last_name' => '', 'phone' => '+44 20 7946 0000', 'new_customer' => 'No', 'service' => 'Acid Wash', 'page' => '/from-referer/' ) );

call_user_func( $sub, wpf( array( 1 => 'Nobody', 2 => '', 3 => '', 4 => 'Other' ) ), array(), array( 'id' => 440 ), 0 );
expect( 'no phone and no e-mail -> nothing', '__HOOK_QUOTE__', null );
call_user_func( $sub, wpf( array( 1 => 'X', 2 => '4805550100' ) ), array(), array( 'id' => 999 ), 0 );
expect( 'other WPForms form -> nothing', '__HOOK_QUOTE__', null );

call_user_func( $GLOBALS['hooks']['rest_api_init'] );
$perm = $GLOBALS['routes']['ps-ghl/v1/status']['permission_callback'];
check( 'routes refuse a wrong/empty key (and the unfilled placeholder)', ! $perm( new KReq( 'wrong' ) ) && ! $perm( new KReq( '' ) ) && ! $perm( new KReq( '__KEY__' ) ) );
$test = $GLOBALS['routes']['ps-ghl/v1/test']['callback'];
$f440 = array( '1' => 'Test Quote', '2' => '4805550140', '3' => 'Yes', '4' => 'Green Pool Clean' );
$r    = $test( new KReq( '', array( 'form_id' => '440', 'fields' => $f440, 'page' => '/' ) ) );
check( 'test route: mapping only', '440' === $r['form'] && 'Test' === $r['data']['first_name'] && null === $r['sent'] && ! $GLOBALS['sent'] );
$r = $test( new KReq( '', array( 'form_id' => '440', 'fields' => $f440, 'send' => true, 'hook' => '__HOOK_QUOTE__' ) ) );
check( 'test route: send to a live webhook refused', $r instanceof WP_Error && ! $GLOBALS['sent'] );
$r = $test( new KReq( '', array( 'form_id' => '440', 'fields' => $f440, 'send' => true ) ) );
check( 'test route: send without a test webhook refused', $r instanceof WP_Error && ! $GLOBALS['sent'] );
$r = $test( new KReq( '', array( 'form_id' => '440', 'fields' => $f440, 'send' => true, 'hook' => 'ZZtestHook0123456789' ) ) );
$got = array_pop( $GLOBALS['sent'] );
check( 'test route: send to the test webhook', 200 === $r['sent'] && PS_GHL::BASE . 'ZZtestHook0123456789' === $got[0] );

$log = get_option( 'ps_ghl_log' );
$ok  = 5 === count( $log ) && 'test' === $log[0][2] && 'live' === $log[1][2] && '+14805550140' === $log[0][3];
check( 'status log (' . count( (array) $log ) . ' entries, live/test marked)', $ok, json_encode( $log ) );
echo $fail ? "\n$fail FAILED\n" : "\nall ok\n";
exit( $fail ? 1 : 0 );
