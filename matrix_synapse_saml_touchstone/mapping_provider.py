# -*- coding: utf-8 -*-
# Copyright 2020 The Matrix.org Foundation C.I.C.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import logging
import random
import string
import time
from typing import Set, Tuple

import attr
import saml2.response

import synapse.module_api
from synapse.api.errors import CodeMessageException
from synapse.module_api.errors import RedirectException

from matrix_synapse_saml_touchstone._sessions import (
    SESSION_COOKIE_NAME,
    DisplayNameMappingSession,
    expire_old_sessions,
    displayname_mapping_sessions,
)

logger = logging.getLogger(__name__)


MAPPING_SESSION_VALIDITY_PERIOD_MS = 15 * 60 * 1000

# names of attributes in the `ava` property we get from pysaml2
UID_ATTRIBUTE_NAME = "uid"
EMAIL_ATTRIBUTE_NAME = "email"
DISPLAYNAME_ATTRIBUTE_NAME = "displayName"
AFFILIATION_ATTRIBUTE_NAME = "affiliation"


@attr.s
class SamlConfig(object):
    # TODO: if we need our own config options, we could use `attr` to reduce boilerplate
    pass


class SamlMappingProvider(object):
    def __init__(
        self, parsed_config: SamlConfig, module_api: synapse.module_api.ModuleApi
    ):
        """A Touchstone-flavoured, Synapse user mapping provider

        Args:
            parsed_config: A configuration object. The result of self.parse_config
        """
        self._random = random.SystemRandom()
        self._config = parsed_config


    def get_remote_user_id(
        self, saml_response: saml2.response.AuthnResponse, client_redirect_url: str
    ):
        """Extracts the remote user id from the SAML response"""
        return saml_response.ava[UID_ATTRIBUTE_NAME][0]
    

    def saml_response_to_user_attributes(
        self,
        saml_response: saml2.response.AuthnResponse,
        failures: int,
        client_redirect_url: str,
    ) -> dict:
        """Maps some text from a SAML response to attributes of a new user
        Args:
            saml_response: A SAML auth response object

            failures: How many times a call to this function with this
                saml_response has resulted in a failure

            client_redirect_url: where the client wants to redirect back to

        Returns:
            dict: A dict containing new user attributes. Possible keys:
                * mxid_localpart (str): Required. The localpart of the user's mxid
                * displayname (str): The displayname of the user
        """
        remote_user_id = self.get_remote_user_id(saml_response, client_redirect_url)
        displayname = saml_response.ava.get(DISPLAYNAME_ATTRIBUTE_NAME, [None])[0]

        expire_old_sessions()

        # make up a cryptorandom session id
        session_id = "".join(
            self._random.choice(string.ascii_letters) for _ in range(16)
        )

        now = int(time.time() * 1000)
        session = DisplayNameMappingSession(
            remote_user_id=remote_user_id,
            displayname=displayname,
            client_redirect_url=client_redirect_url,
            expiry_time_ms=now + MAPPING_SESSION_VALIDITY_PERIOD_MS,
        )

        displayname_mapping_sessions[session_id] = session
        logger.info("Recorded registration session id %s", session_id)

        # Redirect to the display name picker
        e = RedirectException(b"/_matrix/saml2/pick_displayname/")
        e.cookies.append(
            b"%s=%s; path=/" % (SESSION_COOKIE_NAME, session_id.encode("ascii"),)
        )
        raise e

    @staticmethod
    def parse_config(config: dict) -> SamlConfig:
        """Parse the dict provided by the homeserver's config
        Args:
            config: A dictionary containing configuration options for this provider
        Returns:
            SamlConfig: A custom config object
        """
        parsed = SamlConfig()

        return parsed

    @staticmethod
    def get_saml_attributes(config: SamlConfig) -> Tuple[set, set]:
        """Returns the required and optional attributes of a SAML auth response object

        Args:
            config: A SamlConfig object containing configuration options for this provider

        Returns:
            tuple[set,set]: The first set equates to the saml auth response
                attributes that are required for the module to function, whereas the
                second set consists of those attributes which can be used if
                available, but are not necessary
        """
        required = {EMAIL_ATTRIBUTE_NAME, UID_ATTRIBUTE_NAME}
        optional = {UID_ATTRIBUTE_NAME, DISPLAYNAME_ATTRIBUTE_NAME}

        return required, optional
