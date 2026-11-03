<?php
/**
 * The Pool Shack (thepoolshackarizona.com) → GHL sub-account "The Pool Shack". Pool Profits, 03/11/2026.
 *
 * Sends each WPForms submission to its inbound webhook (workflows "Website Form - …", built by scripts/ps_site.py).
 * Runs after WPForms has done everything it does today (validation, reCAPTCHA, its e-mails, confirmation): hook
 * wpforms_process_complete, which only fires for a submission WPForms accepted.
 *
 * Installed as a Code Snippets snippet by scripts/ps_site.py, which fills the __HOOK_*__ ids from
 * backup/the-pool-shack/webhook-urls.json (kept out of git).
 *
 * - 440 "Request a Quote" (home): Name, Phone, Are You a New Customer?, Service Needed.
 * - 443 "Main Contact / Service Form" (home, /contact/): Full Name, Phone, Email, Address, Postal Code, Service Needed,
 *   Message, consent checkbox (not sent: WPForms requires it).
 * - Name is split at the first space (or WPForms' first/last when the field uses that format); US phone → +1XXXXXXXXXX.
 * - Routes for us (admin, or ?key=<KEY>): GET /wp-json/ps-ghl/v1/status (last 30 sends), POST /wp-json/ps-ghl/v1/test
 *   (mapping only; "send" posts only to a webhook id given in "hook" that is not one of the live ones, so a test never
 *   reaches the live workflows and their alerts).
 */

if ( ! class_exists( 'PS_GHL' ) ) {

	class PS_GHL {
		const VERSION = '1.0';
		const BASE    = 'https://services.leadconnectorhq.com/hooks/3CozZ1NfujYWEPIYgzx0/webhook-trigger/';
		const HOOKS   = array(
			'440' => '__HOOK_QUOTE__',
			'443' => '__HOOK_CONTACT__',
		);
		// WPForms form id → field id → payload key.
		const FORMS = array(
			'440' => array( '1' => 'name', '2' => 'phone', '3' => 'new_customer', '4' => 'service' ),
			'443' => array( '1' => 'name', '2' => 'phone', '3' => 'email', '4' => 'address', '5' => 'postal_code',
				'6' => 'service', '7' => 'message' ),
		);
		const KEY = '__KEY__';

		static function init() {
			add_action( 'wpforms_process_complete', array( __CLASS__, 'on_submit' ), 99, 4 );
			add_action( 'rest_api_init', array( __CLASS__, 'routes' ) );
		}

		static function split( $name ) {
			$name  = trim( preg_replace( '/\s+/u', ' ', (string) $name ) );
			$parts = explode( ' ', $name, 2 );
			return array( $parts[0], isset( $parts[1] ) ? $parts[1] : '' );
		}

		static function phone( $v ) {
			$v = trim( (string) $v );
			$d = preg_replace( '/\D+/', '', $v );
			if ( 10 === strlen( $d ) ) {
				return '+1' . $d;
			}
			if ( 11 === strlen( $d ) && '1' === $d[0] ) {
				return '+' . $d;
			}
			return $v;
		}

		static function path( $url ) {
			$path = wp_parse_url( (string) $url, PHP_URL_PATH );
			return $path ? $path : '';
		}

		/**
		 * WPForms fields (id => field array with 'value', or a plain value) → payload, or null when the form is not ours.
		 */
		static function map( $form_id, $fields, $page ) {
			$form_id = (string) $form_id;
			if ( ! isset( self::FORMS[ $form_id ] ) ) {
				return null;
			}
			$data = array();
			foreach ( self::FORMS[ $form_id ] as $fid => $key ) {
				$f = isset( $fields[ $fid ] ) ? $fields[ $fid ] : ( isset( $fields[ (int) $fid ] ) ? $fields[ (int) $fid ] : '' );
				$v = is_array( $f ) ? ( isset( $f['value'] ) ? $f['value'] : '' ) : $f;
				$v = is_scalar( $v ) ? trim( (string) $v ) : '';
				if ( 'name' === $key ) {
					if ( is_array( $f ) && ! empty( $f['first'] ) ) { // first/last format
						$first = trim( (string) $f['first'] );
						$last  = isset( $f['last'] ) ? trim( (string) $f['last'] ) : '';
					} else {
						list( $first, $last ) = self::split( $v );
					}
					$data['first_name'] = $first;
					$data['last_name']  = $last;
				} elseif ( 'phone' === $key ) {
					$data['phone'] = self::phone( $v );
				} elseif ( 'email' === $key ) {
					$data['email'] = strtolower( $v );
				} else {
					$data[ $key ] = $v;
				}
			}
			$data['page'] = $page;
			return $data;
		}

		static function send( $form_id, $data, $hook = null ) {
			$hook = $hook ? $hook : ( isset( self::HOOKS[ $form_id ] ) ? self::HOOKS[ $form_id ] : '' );
			if ( ! $hook || ( empty( $data['email'] ) && empty( $data['phone'] ) ) ) {
				return null;
			}
			$res  = wp_remote_post( self::BASE . $hook, array(
				'headers' => array( 'Content-Type' => 'application/json' ),
				'body'    => wp_json_encode( $data ),
				'timeout' => 8,
			) );
			$code = is_wp_error( $res ) ? $res->get_error_message() : (int) wp_remote_retrieve_response_code( $res );
			if ( 200 !== $code ) {
				error_log( 'ps-ghl: form ' . $form_id . ' -> ' . $code );
			}
			$log = get_option( 'ps_ghl_log', array() );
			array_unshift( $log, array( gmdate( 'c' ), $form_id, isset( self::HOOKS[ $form_id ] ) && self::HOOKS[ $form_id ] === $hook ? 'live' : 'test',
				! empty( $data['email'] ) ? $data['email'] : $data['phone'], $code ) );
			update_option( 'ps_ghl_log', array_slice( $log, 0, 30 ), false );
			return $code;
		}

		static function on_submit( $fields, $entry, $form_data, $entry_id = 0 ) {
			$form_id = isset( $form_data['id'] ) ? (string) $form_data['id'] : '';
			$url     = isset( $_POST['page_url'] ) ? wp_unslash( $_POST['page_url'] ) : wp_get_raw_referer(); // phpcs:ignore
			$data    = self::map( $form_id, (array) $fields, self::path( $url ) );
			if ( $data ) {
				self::send( $form_id, $data );
			}
		}

		static function routes() {
			$admin = function ( $request ) {
				$key = (string) $request->get_param( 'key' );
				return current_user_can( 'manage_options' ) || ( strlen( self::KEY ) >= 20 && hash_equals( self::KEY, $key ) );
			};
			register_rest_route( 'ps-ghl/v1', '/status', array(
				'methods'             => 'GET',
				'permission_callback' => $admin,
				'callback'            => function () {
					return array( 'version' => self::VERSION, 'forms' => self::FORMS, 'log' => get_option( 'ps_ghl_log', array() ) );
				},
			) );
			// {"form_id", "fields": {id: value}, "page", "send": true, "hook": "<test webhook id>"}.
			register_rest_route( 'ps-ghl/v1', '/test', array(
				'methods'             => 'POST',
				'permission_callback' => $admin,
				'callback'            => function ( $request ) {
					$p    = $request->get_json_params();
					$fid  = isset( $p['form_id'] ) ? (string) $p['form_id'] : '';
					$data = self::map( $fid, isset( $p['fields'] ) ? (array) $p['fields'] : array(), isset( $p['page'] ) ? (string) $p['page'] : '' );
					$hook = isset( $p['hook'] ) ? (string) $p['hook'] : '';
					$sent = null;
					if ( $data && ! empty( $p['send'] ) ) {
						if ( ! preg_match( '/^[A-Za-z0-9_-]{10,64}$/', $hook ) || in_array( $hook, self::HOOKS, true ) ) {
							return new WP_Error( 'ps_ghl_test_hook', 'send needs a test webhook id (never a live one)', array( 'status' => 400 ) );
						}
						$sent = self::send( $fid, $data, $hook );
					}
					return array( 'form' => $data ? $fid : null, 'data' => $data, 'sent' => $sent );
				},
			) );
		}
	}

	PS_GHL::init();
}
