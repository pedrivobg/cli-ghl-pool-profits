<?php
/**
 * Bluewater Brokerage → Bill's GHL (BurchTech). Pool Profits, 20/10/2026.
 *
 * Sends each website form to its inbound webhook in the GHL sub-account "Bluewater Brokerage"
 * (workflows "Website - …", built by scripts/bw_forms.py). Runs alongside what the site already does:
 * the emails to Bill, the guide PDFs and the calculator endpoint stay as they are.
 *
 * Installed as a Code Snippets snippet by scripts/bw_site.py, which fills the __HOOK_*__ ids from
 * backup/bluewater-brokerage/webhook-urls.json (kept out of git).
 *
 * - Elementor forms: hook elementor_pro/forms/new_record (after the form's own actions ran).
 * - Route calculator: filter rest_request_after_callbacks on /bwb/v1/route-lead (after the endpoint ran).
 * - Name is split at the first space; checkboxes go as "yes"/"no"; honeypot filled = nothing is sent.
 * - Admin-only routes: GET /wp-json/bwb-ghl/v1/status (last 30 sends), POST /wp-json/bwb-ghl/v1/test.
 */

if ( ! class_exists( 'BWB_GHL' ) ) {

	class BWB_GHL {
		const VERSION = '1.0';
		const BASE    = 'https://services.leadconnectorhq.com/hooks/M6eDjuSa3RdwukFl2rW2/webhook-trigger/';
		const HOOKS   = array(
			'gate'       => '__HOOK_GATE__',
			'figures'    => '__HOOK_FIGURES__',
			'seller'     => '__HOOK_SELLER__',
			'buyer'      => '__HOOK_BUYER__',
			'contact'    => '__HOOK_CONTACT__',
			'newsletter' => '__HOOK_NEWSLETTER__',
		);
		// Elementor form element id → GHL form.
		const FORMS = array(
			'bwr0009'  => 'seller',     // /resources/ BWB Seller Guide
			'bwr0010'  => 'buyer',      // /resources/ BWB Buyer Guide
			'59d31fac' => 'contact',    // home
			'c6411dd'  => 'contact',    // /contact/
			'36394603' => 'newsletter', // footer, every page
		);
		const CALC_ROUTE = '/bwb/v1/route-lead';

		static function init() {
			add_action( 'elementor_pro/forms/new_record', array( __CLASS__, 'on_elementor' ), 10, 2 );
			add_filter( 'rest_request_after_callbacks', array( __CLASS__, 'on_rest' ), 10, 3 );
			add_action( 'rest_api_init', array( __CLASS__, 'routes' ) );
		}

		static function split( $name ) {
			$name  = trim( preg_replace( '/\s+/u', ' ', (string) $name ) );
			$parts = explode( ' ', $name, 2 );
			return array( $parts[0], isset( $parts[1] ) ? $parts[1] : '' );
		}

		static function yn( $v ) {
			if ( is_string( $v ) ) {
				$v = trim( strtolower( $v ) );
				return ( '' === $v || in_array( $v, array( 'no', 'false', '0', 'off' ), true ) ) ? 'no' : 'yes';
			}
			return $v ? 'yes' : 'no';
		}

		static function path( $url ) {
			$path = wp_parse_url( (string) $url, PHP_URL_PATH );
			return $path ? $path : '';
		}

		/** Elementor fields (id => value) → [ghl form, payload], or null when nothing is to be sent. */
		static function map_elementor( $form_id, $f, $page ) {
			if ( ! isset( self::FORMS[ $form_id ] ) || ! empty( $f['hp'] ) ) {
				return null;
			}
			$form = self::FORMS[ $form_id ];
			list( $first, $last ) = self::split( isset( $f['name'] ) ? $f['name'] : '' );
			$who = array( 'first_name' => $first, 'last_name' => $last, 'email' => isset( $f['email'] ) ? trim( $f['email'] ) : '' );
			$v   = function ( $k ) use ( $f ) {
				return isset( $f[ $k ] ) ? trim( (string) $f[ $k ] ) : '';
			};
			switch ( $form ) {
				case 'seller':
					$data = $who + array( 'opinion' => self::yn( $v( 'opinion' ) ) );
					break;
				case 'buyer':
					$data = $who + array( 'register' => self::yn( $v( 'register' ) ) );
					break;
				case 'contact':
					$data = $who + array( 'phone' => $v( 'phone' ), 'message' => $v( 'message' ) );
					break;
				default: // newsletter
					$data = array( 'email' => $who['email'] );
			}
			$data['page'] = $page;
			return array( $form, $data );
		}

		/** Calculator payload ({type, who, figures, website, page}) → [ghl form, payload], or null. */
		static function map_calculator( $p ) {
			if ( ! is_array( $p ) || ! empty( $p['website'] ) ) {
				return null;
			}
			$who = ( isset( $p['who'] ) && is_array( $p['who'] ) ) ? $p['who'] : array();
			$w   = function ( $k ) use ( $who ) {
				return isset( $who[ $k ] ) && is_scalar( $who[ $k ] ) ? trim( (string) $who[ $k ] ) : '';
			};
			list( $first, $last ) = self::split( $w( 'name' ) );
			$base = array( 'first_name' => $first, 'last_name' => $last, 'email' => $w( 'email' ) );
			$page = isset( $p['page'] ) ? self::path( $p['page'] ) : '';
			$type = isset( $p['type'] ) ? $p['type'] : '';
			if ( 'gate' === $type ) {
				return array( 'gate', $base + array(
					'phone'    => $w( 'phone' ),
					'business' => $w( 'business' ),
					'city'     => $w( 'city' ),
					'report'   => self::yn( isset( $who['report'] ) ? $who['report'] : false ),
					'talk'     => self::yn( isset( $who['talk'] ) ? $who['talk'] : false ),
					'page'     => $page,
				) );
			}
			if ( 'figures' === $type ) {
				$fig = ( isset( $p['figures'] ) && is_array( $p['figures'] ) ) ? $p['figures'] : array();
				$data = $base;
				foreach ( array( 'monthly_billing', 'visits_per_week', 'quality_score', 'multiple', 'value_low',
					'value_high', 'equipment_value', 'inventory_value' ) as $k ) {
					$data[ $k ] = isset( $fig[ $k ] ) && is_scalar( $fig[ $k ] ) ? (string) $fig[ $k ] : '';
				}
				$data['is_franchise'] = self::yn( isset( $fig['is_franchise'] ) ? $fig['is_franchise'] : false );
				$data['agreements']   = isset( $fig['has_agreements'] ) && is_scalar( $fig['has_agreements'] ) ? (string) $fig['has_agreements'] : '';
				$data['page']         = $page;
				return array( 'figures', $data );
			}
			return null;
		}

		static function send( $form, $data ) {
			if ( empty( $data['email'] ) || empty( self::HOOKS[ $form ] ) ) {
				return null;
			}
			$res  = wp_remote_post( self::BASE . self::HOOKS[ $form ], array(
				'headers' => array( 'Content-Type' => 'application/json' ),
				'body'    => wp_json_encode( $data ),
				'timeout' => 8,
			) );
			$code = is_wp_error( $res ) ? $res->get_error_message() : (int) wp_remote_retrieve_response_code( $res );
			if ( 200 !== $code ) {
				error_log( 'bwb-ghl: ' . $form . ' -> ' . $code );
			}
			$log = get_option( 'bwb_ghl_log', array() );
			array_unshift( $log, array( gmdate( 'c' ), $form, $data['email'], $code ) );
			update_option( 'bwb_ghl_log', array_slice( $log, 0, 30 ), false );
			return $code;
		}

		static function on_elementor( $record, $handler ) {
			$f = array();
			foreach ( (array) $record->get( 'fields' ) as $id => $field ) {
				$f[ $id ] = isset( $field['value'] ) ? $field['value'] : '';
			}
			$ref = isset( $_POST['referrer'] ) ? wp_unslash( $_POST['referrer'] ) : wp_get_raw_referer(); // phpcs:ignore
			$out = self::map_elementor( (string) $record->get_form_settings( 'id' ), $f, self::path( $ref ) );
			if ( $out ) {
				self::send( $out[0], $out[1] );
			}
		}

		static function on_rest( $response, $handler, $request ) {
			if ( self::CALC_ROUTE !== $request->get_route() || is_wp_error( $response ) ) {
				return $response;
			}
			if ( $response instanceof WP_HTTP_Response && $response->get_status() >= 300 ) {
				return $response;
			}
			$p = $request->get_json_params();
			if ( ! is_array( $p ) ) {
				$p = json_decode( $request->get_body(), true );
			}
			$out = self::map_calculator( $p );
			if ( ! $out ) {
				return $response;
			}
			if ( 'figures' === $out[0] ) { // the page re-sends figures on every tab switch: same numbers go once a day
				$key = 'bwb_ghl_' . md5( wp_json_encode( $out[1] ) );
				if ( get_transient( $key ) ) {
					return $response;
				}
				set_transient( $key, 1, DAY_IN_SECONDS );
			}
			self::send( $out[0], $out[1] );
			return $response;
		}

		static function routes() {
			$admin = function () {
				return current_user_can( 'manage_options' );
			};
			register_rest_route( 'bwb-ghl/v1', '/status', array(
				'methods'             => 'GET',
				'permission_callback' => $admin,
				'callback'            => function () {
					return array( 'version' => self::VERSION, 'forms' => self::FORMS, 'log' => get_option( 'bwb_ghl_log', array() ) );
				},
			) );
			// {"elementor": {"form_id", "fields", "page"}} or {"calculator": <payload>}; "send": true posts it to GHL.
			register_rest_route( 'bwb-ghl/v1', '/test', array(
				'methods'             => 'POST',
				'permission_callback' => $admin,
				'callback'            => function ( $request ) {
					$p = $request->get_json_params();
					if ( isset( $p['elementor'] ) ) {
						$e   = $p['elementor'];
						$out = self::map_elementor( isset( $e['form_id'] ) ? (string) $e['form_id'] : '',
							isset( $e['fields'] ) ? (array) $e['fields'] : array(), isset( $e['page'] ) ? (string) $e['page'] : '' );
					} else {
						$out = self::map_calculator( isset( $p['calculator'] ) ? $p['calculator'] : null );
					}
					$sent = ( $out && ! empty( $p['send'] ) ) ? self::send( $out[0], $out[1] ) : null;
					return array( 'form' => $out ? $out[0] : null, 'data' => $out ? $out[1] : null, 'sent' => $sent );
				},
			) );
		}
	}

	BWB_GHL::init();
}
