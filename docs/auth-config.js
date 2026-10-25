/* Waste Intelligence — auth configuration (public, client-side values only).
 *
 * Email accounts work out of the box, stored in this browser only (see
 * auth.js). Google and Apple sign-in cannot run on a static Pages site
 * without an OAuth client registered for this exact Pages origin — there
 * is no provider account or key in this repo, so both providers start
 * UNCONFIGURED and their buttons open the setup panel instead of faking
 * a sign-in. To enable one:
 *
 *  Google: create an OAuth client ID in Google Cloud Console, add the
 *  Pages origin (https://ecocode-smart-city-infrastructure.github.io)
 *  as an authorised JavaScript origin, then set googleClientId below.
 *  Apple: create a Service ID in Apple Developer, add this page's URL as
 *  a return URL, then set appleClientId below.
 *
 *  For shared accounts across devices, or server-verified identities,
 *  replace this local store with Firebase Auth, Auth0, or Supabase —
 *  those services own the account database and token verification.
 *  Nothing in this file is a secret: never put a client secret here.
 */
window.WI_AUTH_CONFIG = {
  googleClientId: '',
  appleClientId: '',
  appleRedirectUri: ''
};
