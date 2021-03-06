# -*- coding: utf-8 -*-
import urlparse
from base64 import urlsafe_b64decode, urlsafe_b64encode

from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory
from django.test.utils import override_settings

import mock

from olympia.accounts import utils
from olympia.users.models import UserProfile

FXA_CONFIG = {
    'default': {
        'client_id': 'foo',
        'client_secret': 'bar',
        'oauth_host': 'https://accounts.firefox.com/oauth',
        'redirect_url': 'https://testserver/fxa',
        'scope': 'profile',
    },
}


@override_settings(FXA_CONFIG=FXA_CONFIG)
def test_fxa_config_anonymous():
    request = RequestFactory().get('/en-US/firefox/addons')
    request.session = {'fxa_state': 'thestate!'}
    request.user = AnonymousUser()
    assert utils.fxa_config(request) == {
        'clientId': 'foo',
        'state': 'thestate!',
        'oauthHost': 'https://accounts.firefox.com/oauth',
        'redirectUrl': 'https://testserver/fxa',
        'scope': 'profile',
    }


@override_settings(FXA_CONFIG=FXA_CONFIG)
def test_fxa_config_logged_in():
    request = RequestFactory().get('/en-US/firefox/addons')
    request.session = {'fxa_state': 'thestate!'}
    request.user = UserProfile(email='me@mozilla.org')
    assert utils.fxa_config(request) == {
        'clientId': 'foo',
        'state': 'thestate!',
        'email': 'me@mozilla.org',
        'oauthHost': 'https://accounts.firefox.com/oauth',
        'redirectUrl': 'https://testserver/fxa',
        'scope': 'profile',
    }


@override_settings(FXA_CONFIG=FXA_CONFIG)
def test_default_fxa_login_url_with_state():
    path = '/en-US/addons/abp/?source=ddg'
    request = RequestFactory().get(path)
    request.session = {'fxa_state': 'myfxastate'}
    raw_url = utils.default_fxa_login_url(request)
    url = urlparse.urlparse(raw_url)
    base = '{scheme}://{netloc}{path}'.format(
        scheme=url.scheme, netloc=url.netloc, path=url.path)
    assert base == 'https://accounts.firefox.com/oauth/authorization'
    query = urlparse.parse_qs(url.query)
    next_path = urlsafe_b64encode(path).rstrip('=')
    assert query == {
        'action': ['signin'],
        'client_id': ['foo'],
        'redirect_url': ['https://testserver/fxa'],
        'scope': ['profile'],
        'state': ['myfxastate:{next_path}'.format(next_path=next_path)],
    }


@override_settings(FXA_CONFIG=FXA_CONFIG)
def test_default_fxa_register_url_with_state():
    path = '/en-US/addons/abp/?source=ddg'
    request = RequestFactory().get(path)
    request.session = {'fxa_state': 'myfxastate'}
    raw_url = utils.default_fxa_register_url(request)
    url = urlparse.urlparse(raw_url)
    base = '{scheme}://{netloc}{path}'.format(
        scheme=url.scheme, netloc=url.netloc, path=url.path)
    assert base == 'https://accounts.firefox.com/oauth/authorization'
    query = urlparse.parse_qs(url.query)
    next_path = urlsafe_b64encode(path).rstrip('=')
    assert query == {
        'action': ['signup'],
        'client_id': ['foo'],
        'redirect_url': ['https://testserver/fxa'],
        'scope': ['profile'],
        'state': ['myfxastate:{next_path}'.format(next_path=next_path)],
    }


def test_unicode_next_path():
    path = u'/en-US/føø/bãr'
    request = RequestFactory().get(path)
    request.session = {}
    url = utils.default_fxa_login_url(request)
    state = urlparse.parse_qs(urlparse.urlparse(url).query)['state'][0]
    next_path = urlsafe_b64decode(state.split(':')[1] + '===')
    assert next_path.decode('utf-8') == path


@mock.patch('olympia.accounts.utils.default_fxa_login_url')
def test_redirect_for_login(default_fxa_login_url):
    login_url = 'https://example.com/login'
    default_fxa_login_url.return_value = login_url
    request = mock.MagicMock()
    response = utils.redirect_for_login(request)
    default_fxa_login_url.assert_called_with(request)
    assert response['location'] == login_url
