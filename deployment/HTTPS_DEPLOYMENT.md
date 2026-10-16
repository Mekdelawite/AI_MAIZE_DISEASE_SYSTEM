# HTTPS Deployment Requirement

Production deployment must use HTTPS/TLS.

Local development may use http://127.0.0.1:5000.

Production HTTPS should be provided by the deployment platform or reverse proxy.

Required controls: valid TLS certificate, HTTP to HTTPS redirect, no TLS private keys committed to Git, production secrets stored securely, secure cookies where applicable, and Flask kept behind the production reverse proxy.

HTTPS is a deployment-layer requirement and does not require changing the local Flask development server.

Status: HTTPS must be enabled before public production deployment.
