[general]
# Service tag/version reported in the JSON responses.
TAG: 0.1


[web]
# type of access control for the web front end. supports: 'jwt', and 'none'
access_control: jwt
#access_control: none

# the name of the tenant when not using jwt
tenant_name: dev_staging

# public key for the apim instance when deployed behind apim (jwt access control)
apim_pub_key: MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQCUp/oV1vWc8/TkQSiAvTousMzOM4asB2iltr2QKozni5aVFu818MpOLZIr8LMnTzWllJvvaA5RAAdpbECb+48FjbBe0hseUdN5HpwvnH/DW8ZccGvk53I6Orq7hLCv1ZHtuOCokghz/ATrhyPq+QktMfXnRS4HrKGJTzxaCcU7OQIDAQAB

# whether to show tracebacks on error
show_traceback: True

