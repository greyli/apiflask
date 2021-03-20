import pytest
from openapi_spec_validator import validate_spec

from apiflask import APIBlueprint, input

from .schemas import QuerySchema, FooSchema


def test_openapi_fields(app, client):
    description = 'My API'
    tags = [
        {
            'name': 'foo',
            'description': 'some description for foo',
            'externalDocs': {
                'description': 'Find more info about foo here',
                'url': 'https://docs.example.com/'
            }
        },
        {'name': 'bar', 'description': 'some description for bar'},
    ]
    contact = {
        'name': 'API Support',
        'url': 'http://www.example.com/support',
        'email': 'support@example.com'
    }
    license = {
        'name': 'Apache 2.0',
        'url': 'http://www.apache.org/licenses/LICENSE-2.0.html'
    }
    terms_of_service = 'http://example.com/terms/'
    external_docs = {
        'description': 'Find more info here',
        'url': 'https://docs.example.com/'
    }
    servers = [
        {
            'url': 'http://localhost:5000/',
            'description': 'Development server'
        },
        {
            'url': 'https://api.example.com/',
            'description': 'Production server'
        }
    ]
    app.config['DESCRIPTION'] = description
    app.config['TAGS'] = tags
    app.config['CONTACT'] = contact
    app.config['LICENSE'] = license
    app.config['TERMS_OF_SERVICE'] = terms_of_service
    app.config['EXTERNAL_DOCS'] = external_docs
    app.config['SERVERS'] = servers

    rv = client.get('/openapi.json')
    assert rv.status_code == 200
    validate_spec(rv.json)
    assert rv.json['tags'] == tags
    assert rv.json['servers'] == servers
    assert rv.json['externalDocs'] == external_docs
    assert rv.json['info']['description'] == description
    assert rv.json['info']['contact'] == contact
    assert rv.json['info']['license'] == license
    assert rv.json['info']['termsOfService'] == terms_of_service


@pytest.mark.parametrize('spec_format', ['json', 'yaml', 'yml'])
def test_spec_format(app, spec_format):
    app.config['SPEC_FORMAT'] = spec_format
    spec = app.spec
    if spec_format == 'json':
        assert isinstance(spec, dict)
    else:
        assert 'title: APIFlask' in spec


def test_auto_tags(app, client):
    bp = APIBlueprint('foo', __name__)
    app.config['AUTO_TAGS'] = False

    @bp.get('/')
    def foo():
        pass

    app.register_blueprint(bp)
    rv = client.get('/openapi.json')
    assert rv.status_code == 200
    validate_spec(rv.json)
    assert rv.json['tags'] == []
    assert 'tags' not in rv.json['paths']['/']['get']


def test_auto_description(test_apps):
    from auto_description import app

    app.config['AUTO_DESCRIPTION'] = False

    spec = app.spec
    validate_spec(spec)
    assert 'description' not in spec['info']

    # reset the app status
    app._spec = None
    app.config['AUTO_DESCRIPTION'] = True


@pytest.mark.parametrize('config_value', [True, False])
def test_auto_path_summary(app, client, config_value):
    app.config['AUTO_PATH_SUMMARY'] = config_value

    @app.get('/foo')
    def get_foo():
        pass

    rv = client.get('/openapi.json')
    assert rv.status_code == 200
    validate_spec(rv.json)
    if config_value:
        assert rv.json['paths']['/foo']['get']['summary'] == 'Get Foo'
    else:
        assert 'summary' not in rv.json['paths']


@pytest.mark.parametrize('config_value', [True, False])
def test_auto_path_description(app, client, config_value):
    app.config['AUTO_PATH_DESCRIPTION'] = config_value

    @app.get('/foo')
    def get_foo():
        """Get a Foo

        some description
        """
        pass

    rv = client.get('/openapi.json')
    assert rv.status_code == 200
    validate_spec(rv.json)
    if config_value:
        assert rv.json['paths']['/foo']['get']['description'] == 'some description'
    else:
        assert 'description' not in rv.json['paths']


@pytest.mark.parametrize('config_value', [True, False])
def test_auto_200_response(app, client, config_value):
    app.config['AUTO_200_RESPONSE'] = config_value

    @app.get('/foo')
    def foo():
        pass

    rv = client.get('/openapi.json')
    assert rv.status_code == 200
    validate_spec(rv.json)
    assert bool('/foo' in rv.json['paths']) is config_value


@pytest.mark.parametrize('config_value', [True, False])
def test_auto_204_response(app, client, config_value):
    app.config['AUTO_204_RESPONSE'] = config_value

    @app.get('/foo')
    @input(QuerySchema, 'query')
    def foo():
        pass

    rv = client.get('/openapi.json')
    assert rv.status_code == 200
    validate_spec(rv.json)
    assert '/foo' in rv.json['paths']
    assert bool('204' in rv.json['paths']['/foo']['get']['responses']) is config_value


def test_response_description_config(app, client):
    app.config['DESCRIPTION_FOR_200'] = 'It works'
    app.config['DESCRIPTION_FOR_204'] = 'Nothing'

    @app.get('/foo')
    @input(FooSchema)
    def only_body_schema(foo):
        pass

    @app.get('/bar')
    def no_schema():
        pass

    rv = client.get('/openapi.json')
    assert rv.status_code == 200
    validate_spec(rv.json)
    assert rv.json['paths']['/foo']['get']['responses'][
        '204']['description'] == 'Nothing'
    assert rv.json['paths']['/bar']['get']['responses'][
        '200']['description'] == 'It works'


def test_validation_error_config(app, client):
    app.config['VALIDATION_ERROR_CODE'] = 422
    app.config['VALIDATION_ERROR_DESCRIPTION'] = 'Bad'

    @app.post('/foo')
    @input(FooSchema)
    def foo():
        pass

    rv = client.get('/openapi.json')
    assert rv.status_code == 200
    validate_spec(rv.json)
    assert rv.json['paths']['/foo']['post']['responses']['422'] is not None
    assert rv.json['paths']['/foo']['post']['responses'][
        '422']['description'] == 'Bad'


def test_docs_hide_blueprints(app, client):
    bp = APIBlueprint('foo', __name__, tag='test')

    @bp.get('/foo')
    def foo():
        pass

    app.config['DOCS_HIDE_BLUEPRINTS'] = ['foo']
    app.register_blueprint(bp)

    rv = client.get('/openapi.json')
    assert rv.status_code == 200
    validate_spec(rv.json)
    assert rv.json['tags'] == []
    assert '/foo' not in rv.json['paths']


def test_docs_favicon(app, client):
    app.config['DOCS_FAVICON'] = '/my-favicon.png'

    rv = client.get('/docs')
    assert rv.status_code == 200
    assert b'href="/my-favicon.png"' in rv.data


@pytest.mark.parametrize('config_value', [True, False])
def test_docs_use_google_font(app, client, config_value):
    app.config['REDOC_USE_GOOGLE_FONT'] = config_value

    rv = client.get('/redoc')
    assert rv.status_code == 200
    assert bool(b'fonts.googleapis.com' in rv.data) is config_value


def test_redoc_standalone_js(app, client):
    app.config['REDOC_STANDALONE_JS'] = 'https://cdn.example.com/redoc.js'

    rv = client.get('/redoc')
    assert rv.status_code == 200
    assert b'src="https://cdn.example.com/redoc.js"' in rv.data


def test_swagger_ui_resources(app, client):
    app.config['SWAGGER_UI_CSS'] = 'https://cdn.example.com/swagger-ui.css'
    app.config['SWAGGER_UI_BUNDLE_JS'] = 'https://cdn.example.com/swagger-ui.bundle.js'
    app.config['SWAGGER_UI_STANDALONE_PRESET_JS'] = \
        'https://cdn.example.com/swagger-ui.preset.js'

    rv = client.get('/docs')
    assert rv.status_code == 200
    assert b'href="https://cdn.example.com/swagger-ui.css"' in rv.data
    assert b'src="https://cdn.example.com/swagger-ui.bundle.js"' in rv.data
    assert b'src="https://cdn.example.com/swagger-ui.preset.js"' in rv.data


def test_swagger_ui_layout(app, client):
    app.config['SWAGGER_UI_LAYOUT'] = 'StandaloneLayout'

    rv = client.get('/docs')
    assert rv.status_code == 200
    assert b'StandaloneLayout' in rv.data
    assert b'BaseLayout' not in rv.data


def test_swagger_ui_config(app, client):
    app.config['SWAGGER_UI_CONFIG'] = {
        'deepLinking': False,
        'layout': 'StandaloneLayout'
    }

    rv = client.get('/docs')
    assert rv.status_code == 200
    assert b'"deepLinking": false' in rv.data
    assert b'"layout": "StandaloneLayout"' in rv.data


def test_swagger_ui_oauth_config(app, client):
    app.config['SWAGGER_UI_OAUTH_CONFIG'] = {
        'clientId': 'foo',
        'usePkceWithAuthorizationCodeGrant': True
    }

    rv = client.get('/docs')
    assert rv.status_code == 200
    assert b'ui.initOAuth(' in rv.data
    assert b'"clientId": "foo"' in rv.data
    assert b'"usePkceWithAuthorizationCodeGrant": true' in rv.data
