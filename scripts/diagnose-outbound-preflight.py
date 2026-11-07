"""Compare private outbound preflight settings using two GET requests only."""

import getpass
import re
import time
from urllib.parse import quote
import httpx
from insurance_operations.telephony.outbound.prompt import DEMO_PROMPT, FIRST_MESSAGE
E164 = re.compile(r'\+[1-9][0-9]{7,14}\Z')


def main() -> None:
    if input('Render OUTBOUND_DEMO_TRANSFER_ENABLED is false? Type YES: ').strip() != 'YES':
        raise SystemExit('This comparison requires OUTBOUND_DEMO_TRANSFER_ENABLED=false.')
    key = getpass.getpass('Render ELEVENLABS_API_KEY: ').strip()
    agent_id = getpass.getpass('Render OUTBOUND_DEMO_AGENT_ID: ').strip()
    phone_id = getpass.getpass('Render OUTBOUND_DEMO_PHONE_NUMBER_ID: ').strip()
    destination = getpass.getpass('Attempted recipient in canonical E.164: ').strip()
    allowed = set(filter(None, (x.strip() for x in getpass.getpass(
        'Render OUTBOUND_DEMO_ALLOWED_NUMBERS: ').split(','))))
    human = getpass.getpass('Render OUTBOUND_DEMO_HUMAN_NUMBER, blank if unset: ').strip()
    maximum = int(input('Render OUTBOUND_DEMO_MAX_DURATION_SECONDS, Enter if unset: ') or '180')
    if not all((key, agent_id, phone_id, destination)) or E164.fullmatch(destination) is None:
        raise SystemExit('Required values missing or recipient is not canonical E.164.')

    def obj(value):
        return value if isinstance(value, dict) else {}

    def results(label, checks):
        for name, passed in checks.items():
            print(label, name, 'PASS' if passed else 'FAIL')

    with httpx.Client(base_url='https://api.elevenlabs.io', timeout=12,
                      follow_redirects=False) as client:
        for label, path in (
            ('agent', '/v1/convai/agents/' + quote(agent_id, safe='')),
            ('phone', '/v1/convai/phone-numbers/' + quote(phone_id, safe='')),
        ):
            started = time.monotonic()
            try:
                response = client.get(path, headers={'xi-api-key': key})
                print(label, 'HTTP', response.status_code,
                      'seconds', round(time.monotonic() - started, 2))
                if response.status_code != 200:
                    continue
                value = response.json()
                if not isinstance(value, dict):
                    print(label, 'object_response FAIL')
                    continue
            except (httpx.HTTPError, ValueError) as error:
                print(label, 'GET failed', type(error).__name__)
                continue
            if label == 'agent':
                config = obj(value.get('conversation_config'))
                agent = obj(config.get('agent'))
                prompt = obj(agent.get('prompt'))
                platform = obj(value.get('platform_settings'))
                workspace = obj(platform.get('workspace_overrides'))
                privacy = obj(platform.get('privacy'))
                hooks = obj(workspace.get('webhooks'))
                duration = obj(config.get('conversation')).get('max_duration_seconds')
                explicit = prompt.get('tools') or []
                tools_valid = isinstance(explicit, list)
                tools = (explicit if tools_valid else []) + [
                    tool for tool in obj(prompt.get('built_in_tools')).values()
                    if tool is not None
                ]
                results(label, {
                    'resource_id_matches': value.get('agent_id') == agent_id,
                    'duration_within_render_limit': type(duration) is int and 1 <= duration <= maximum,
                    'first_message_matches_repo': agent.get('first_message') == FIRST_MESSAGE,
                    'system_prompt_matches_repo': str(prompt.get('prompt', '')).strip() == DEMO_PROMPT.strip(),
                    'recording_off': privacy.get('record_voice') is False,
                    'retention_zero': privacy.get('retention_days') == 0,
                    'agent_auth_enabled': obj(platform.get('auth')).get('enable_auth') is True,
                    'no_knowledge_base': not prompt.get('knowledge_base'),
                    'no_language_presets': not config.get('language_presets'),
                    'no_procedures': not value.get('procedures'),
                    'no_initiation_webhook': not obj(workspace.get('conversation_initiation_client_data_webhook')).get('url'),
                    'post_call_webhook_assigned': bool(hooks.get('post_call_webhook_id')),
                    'required_webhook_events': all(event in (hooks.get('events') or []) for event in ('transcript', 'call_initiation_failure')),
                    'tool_configuration_valid': tools_valid and all(
                        isinstance(tool, dict) for tool in tools),
                    'native_phone_transfer_disabled': not any(
                        obj(tool).get('type') == 'system'
                        and obj(obj(tool).get('params')).get('system_tool_type') == 'transfer_to_number'
                        for tool in tools),
                    'native_end_call_present': any(
                        obj(tool).get('type') == 'system'
                        and obj(obj(tool).get('params')).get('system_tool_type') == 'end_call'
                        for tool in tools),
                })
            else:
                trunk = obj(value.get('outbound_trunk'))
                caller = value.get('phone_number')
                results(label, {
                    'resource_id_matches': value.get('phone_number_id') == phone_id,
                    'sip_provider': value.get('provider') == 'sip_trunk',
                    'telnyx_address': trunk.get('address') == 'sip.telnyx.com',
                    'tls_transport': trunk.get('transport') == 'tls',
                    'digest_configured': trunk.get('has_auth_credentials') is True,
                    'canonical_caller': isinstance(caller, str) and E164.fullmatch(caller) is not None,
                    'caller_differs_from_recipient': caller != destination,
                    'caller_not_in_allowlist': isinstance(caller, str) and caller not in allowed,
                    'caller_differs_from_human': caller != human,
                })


if __name__ == "__main__":
    main()
