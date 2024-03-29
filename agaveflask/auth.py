# Utilities for authn/z
import base64
import re

from Crypto.Signature import PKCS1_v1_5
from Crypto.PublicKey import RSA
from Crypto.Hash import SHA256
from flask import g, request
import jwt

from .config import Config
from .errors import PermissionsError

from logs import get_logger
logger = get_logger(__name__)


jwt.verify_methods['SHA256WITHRSA'] = (
    lambda msg, key, sig: PKCS1_v1_5.new(key).verify(SHA256.new(msg), sig))
jwt.prepare_key_methods['SHA256WITHRSA'] = jwt.prepare_RS_key


def get_pub_key():
    pub_key = Config.get('web', 'apim_public_key')
    return RSA.importKey(base64.b64decode(pub_key))


TOKEN_RE = re.compile('Bearer (.+)')


def get_pub_key():
    pub_key = Config.get('web', 'apim_public_key')
    return RSA.importKey(base64.b64decode(pub_key))


def authn_and_authz(authn_callback=None, authz_callback=None):
    """All-in-one convenience function for implementing the basic Agave authentication
    and authorization on a flask app. 
    
    Pass authn_callback, a Python callable, to handle custom authentication mechanisms (such as nonce) when a JWT
    is not present. (Only called when JWT is not present; not called when JWT is invalid.
    
    Pass authz_callback, a Python callable, to do additional custom authorization
    checks within your app after the initial checks.

    Basic usage is as follows:

    import auth

    my_app = Flask(__name__)
    @my_app.before_request
    def authnz_for_my_app():
        auth.authn_and_authz()

    """
    authentication(authn_callback)
    authorization(authz_callback)


def authentication(authn_callback=None):
    """Entry point for authentication. Use as follows:

    import auth

    my_app = Flask(__name__)
    @my_app.before_request
    def authn_for_my_app():
        auth.authentication()

    """
    # don't control access to OPTIONS verb
    if request.method == 'OPTIONS':
        return
    access_control_type = Config.get('web', 'access_control')
    if access_control_type == 'none':
        g.user = 'anonymous'
        g.token = 'N/A'
        g.tenant = request.headers.get('tenant') or Config.get('web', 'tenant_name')
        g.api_server = get_api_server(g.tenant)
        # with access_control_type NONE, we grant all permissions:
        g.roles = ['ALL']
        return
    elif access_control_type == 'jwt':
        try:
            jwt_header_name, jwt_header, tenant_name = jwt_exists(request)
            return check_jwt(jwt_header_name, jwt_header, tenant_name, request)
        except PermissionsError as e:
            if authn_callback:
                authn_callback()
            else:
                raise e
    else:
        raise PermissionsError(msg='Invalid access_control')


def jwt_exists(req):
    """Check if a JWT header is present in the request, req."""
    tenant_name = None
    jwt_header = None
    for k, v in req.headers.items():
        if k.startswith('X-Jwt-Assertion-'):
            tenant_name = k.split('X-Jwt-Assertion-')[1]
            jwt_header_name = k
            jwt_header = v
            return jwt_header_name, jwt_header, tenant_name
    else:
        # never found a jwt; look for 'Assertion'
        try:
            jwt_header = req.headers['Assertion']
            jwt_header_name = 'Assertion'
            tenant_name = 'dev_staging'
        except KeyError:
            raise PermissionsError(msg='JWT header missing.')
    return jwt_header_name, jwt_header, tenant_name


def check_jwt(jwt_header_name, jwt_header, tenant_name, req):
    """Check for and validate a JWT in a request. """
    try:
        PUB_KEY = get_pub_key()
        decoded = jwt.decode(jwt_header, PUB_KEY)
        g.jwt_header_name = jwt_header_name
        g.jwt = jwt_header
        g.jwt_decoded = decoded
        g.tenant = tenant_name.upper()
        g.api_server = get_api_server(tenant_name)
        g.jwt_server = get_jwt_server()
        g.user = decoded['http://wso2.org/claims/enduser'].split('@')[0]
        g.token = get_token(req.headers)
    except (jwt.DecodeError, KeyError):
        logger.warn("Invalid JWT")
        raise PermissionsError(msg='Invalid JWT.')
    try:
        g.roles_str = decoded['http://wso2.org/claims/role']
    except KeyError:
        # without a roles string, we won't throw an error but will assume the user has no roles.
        logger.warn("Could not decode the roles_str from the JWT.")
        g.roles = []
        return
    # WSO2 APIM roles are returned as a single string, delineated by comma (',') characters.
    g.roles = g.roles_str.split(',')



def get_api_server(tenant_name):
    # todo - lookup tenant in tenants table
    if tenant_name.upper() == '3DEM':
        return 'https://api.3dem.org'
    if tenant_name.upper() == 'AGAVE-PROD':
        return 'https://public.agaveapi.co'
    if tenant_name.upper() == 'ARAPORT-ORG':
        return 'https://api.araport.org'
    if tenant_name.upper() == 'DESIGNSAFE':
        return 'https://agave.designsafe-ci.org'
    if tenant_name.upper() == 'DEV-STAGING':
        return 'https://dev.tenants.aloestaging.tacc.cloud'
    if tenant_name.upper() == 'DEV':
        return 'https://dev.tenants.aloestaging.tacc.cloud'
    if tenant_name.upper() == 'DEV-DEVELOP':
        return 'https://dev.tenants.aloedev.tacc.cloud'
    if tenant_name.upper() == 'IPLANTC-ORG':
        return 'https://agave.iplantc.org'
    if tenant_name.upper() == 'IREC':
        return 'https://irec.tenants.prod.tacc.cloud'
    if tenant_name.upper() == 'PORTALS':
        return 'https://portals-api.tacc.utexas.edu'
    if tenant_name.upper() == 'TACC-PROD':
        return 'https://api.tacc.utexas.edu'
    if tenant_name.upper() == 'A2CPS':
        return 'https://api.a2cps.org'
    if tenant_name.upper() == 'SD2E':
        return 'https://api.sd2e.org'
    if tenant_name.upper() == 'SGCI':
        return 'https://agave.sgci.org'
    if tenant_name.upper() == 'VDJSERVER-ORG':
        return 'https://vdj-agave-api.tacc.utexas.edu'
    return 'http://172.17.0.1:8000'

def get_jwt_server():
    return 'http://api.prod.agaveapi.co'

def get_token(headers):
    """
    :type headers: dict
    :rtype: str|None
    """
    auth = headers.get('Authorization', '')
    match = TOKEN_RE.match(auth)
    if not match:
        return None
    else:
        return match.group(1)

def authorization(authz_callback=None):
    """Entry point for authorization. Use as follows:

    import auth

    my_app = Flask(__name__)
    @my_app.before_request
    def authz_for_my_app():
        auth.authorization()

    """
    if request.method == 'OPTIONS':
        # allow all users to make OPTIONS requests
        return

    if authz_callback:
        authz_callback()
