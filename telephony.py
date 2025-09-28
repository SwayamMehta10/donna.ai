from dotenv import load_dotenv
import os
from contextlib import asynccontextmanager
import json
import logging
from twilio.rest import Client

from livekit import api
from livekit.api import (LiveKitAPI,
                         RoomConfiguration,
                         RoomAgentDispatch)

from livekit.protocol.sip import (CreateSIPInboundTrunkRequest, 
                                  CreateSIPDispatchRuleRequest, 
                                  CreateSIPOutboundTrunkRequest,
                                  SIPInboundTrunkInfo,
                                  SIPOutboundTrunkInfo,
                                  SIPDispatchRuleInfo,
                                  SIPDispatchRuleIndividual,
                                  SIPDispatchRule,
                                  CreateSIPParticipantRequest,
                                  ListSIPDispatchRuleRequest,
                                  ListSIPInboundTrunkRequest,
                                  ListSIPOutboundTrunkRequest)

load_dotenv()

# lkapi in context
@asynccontextmanager
async def livekit_client():
    lkapi = api.LiveKitAPI(
        url=os.getenv("LIVEKIT_URL"),
        api_key=os.getenv("LIVEKIT_API_KEY"),
        api_secret=os.getenv("LIVEKIT_API_SECRET")
    )
    try:
        yield lkapi
    finally:
        await lkapi.aclose()


############################################################################################
# Create twilio inbound setup
############################################################################################

async def setup_twilio_inbound_call(twilio_sid, twilio_auth, twilio_number, unique_code):
    try:
        twilio_Client = Client(username=twilio_sid, password=twilio_auth)

        # Fetch all trunks and check if one already exists with the same friendly name
        existing_trunks = twilio_Client.trunking.v1.trunks.list()
        existing_trunk = next((t for t in existing_trunks if t.friendly_name == f"{unique_code}_{twilio_number}_trunk"), None)

        if existing_trunk:
            trunk = existing_trunk
            logging.info(f"Using existing trunk: {trunk.sid}")
        else:
            trunk = twilio_Client.trunking.v1.trunks.create(friendly_name=f"{unique_code}_{twilio_number}_trunk")
            logging.info(f"Twilio SIP trunk -- Trunk SID = {trunk.sid}")

        # set sip URI as twilio origination url
        origination_uri = os.getenv("LIVEKIT_SIP_URI")+";transport=tcp"

        # Check if origination URI already exists
        uri_list = twilio_Client.trunking.v1.trunks(trunk.sid).origination_urls.list()

        if not any(uri.sip_url == origination_uri for uri in uri_list):
            uri = twilio_Client.trunking.v1.trunks(trunk.sid).origination_urls.create(
                friendly_name=f"{unique_code}_origination_uri",
                weight=1,
                priority=1,
                enabled=True,
                sip_url=origination_uri
            )
            logging.info(f"Created new Origination URI: {uri.sid}")
        else:
            uri = next(uri for uri in uri_list if uri.sip_url == origination_uri)
            logging.info(f"Using existing Origination URI: {uri.sid}")

        # fetch twilio number's sid
        number_info = twilio_Client.incoming_phone_numbers.list(phone_number=twilio_number)

        if not number_info:
            raise Exception(f"No Twilio number found for {twilio_number}")
        
        number_sid = number_info[0].sid        
        logging.info(f"Twilio Number -- SID = {number_sid}")

        # Check current trunk assigned to number
        current_number_config = number_info[0]

        if current_number_config.trunk_sid and current_number_config.trunk_sid != trunk.sid:
            raise ValueError(f"Phone number is already bound to trunk SID: {current_number_config.trunk_sid}")
        
        # Bind number to trunk (voice_url left empty intentionally if SIP is handled)
        twilio_Client.incoming_phone_numbers(sid=number_sid).update(
            voice_receive_mode="voice",
            voice_url="",  
            trunk_sid=trunk.sid
        )
        logging.info(f"Configured number {twilio_number} with trunk {trunk.sid}")

        return  {
            "trunk_sid": trunk.sid,
            "origination_uri_sid":uri.sid,
            "number_sid": number_sid
        }

    except Exception as e:
        logging.error(f"Exception Hit -- Function: setup_twilio_inbound_call --", exc_info=True)
        return {"error": str(e)}



############################################################################################
# Create LiveKit inbound trunk and dispatch
############################################################################################
async def create_livekit_inbound_trunk(twilio_number, unique_code, agent_name, metadata):
    try:
        async with livekit_client() as lkapi:        
        
            # Check for existing or create new inbound trunk 

            trunk_name = f"{unique_code}_{twilio_number}_LK_inboundTrunk"

            try:
            # checking existing
                existing_trunks = await lkapi.sip.list_sip_inbound_trunk(ListSIPInboundTrunkRequest())

                for trunk in ((existing_trunks.ListFields()[0])[1]):
                    if trunk.name == trunk_name:
                        logging.info(f"LiveKit trunk already exists for {twilio_number} - ID: {trunk.sip_trunk_id}")

                        return {
                            "sip_trunk_id": trunk.sip_trunk_id,
                            "sip_dispatch_rule_id": None  # We'll not duplicate dispatch in this case
                        }
            except Exception as e:
                logging.info(f"No existing trunk found that matches our name")        

            # creating new
            inbound_trunk_info = SIPInboundTrunkInfo(name=trunk_name,
                                                     metadata=metadata,
                                                    numbers=[twilio_number])
            
            inbound_trunk_request = CreateSIPInboundTrunkRequest(trunk=inbound_trunk_info)

            inbound_trunk = await lkapi.sip.create_sip_inbound_trunk(create=inbound_trunk_request)
            logging.info(f"Inbound trunking with LiveKit created - SIP TRUNK ID: {inbound_trunk.sip_trunk_id}")

            # create individual dispatch
            logging.info(f"Metadata: {metadata}")
            dispatch_rule_type = SIPDispatchRule(dispatch_rule_individual=SIPDispatchRuleIndividual(room_prefix=unique_code))
            agent_dispatch = RoomAgentDispatch(agent_name=agent_name, metadata=metadata)
            dispatch_agent_in_room = RoomConfiguration(agents=[agent_dispatch], )

            dispatch_rule_request = CreateSIPDispatchRuleRequest(rule=dispatch_rule_type,
                                                                name=f"{unique_code}_dispatch",
                                                                hide_phone_number=False,
                                                                metadata=metadata,
                                                                trunk_ids=[inbound_trunk.sip_trunk_id],
                                                                room_config=dispatch_agent_in_room)
            
            dispatch_rule = await lkapi.sip.create_sip_dispatch_rule(create=dispatch_rule_request)
            logging.info(f"Dispatch rule created - SIP DISPATCH RULE ID: {dispatch_rule.sip_dispatch_rule_id}")


            ret = {
                "sip_trunk_id": inbound_trunk.sip_trunk_id,
                "sip_dispatch_rule_id": dispatch_rule.sip_dispatch_rule_id}
            
            return ret
    
    except Exception as e:
        logging.info(f"Exception Hit -- Function: setup_livekit_inbound_call -- Error: {e}")

############################################################################################
# Create twilio outubound setup
############################################################################################
async def setup_twilio_outbound_call(twilio_number,twilio_sid, twilio_auth, unique_code, outbound_trunk_sid=None):
    try:

        twilio_Client = Client(username=twilio_sid, password=twilio_auth)

        trunk_name = f"{unique_code}_{twilio_number}_trunk"

        existing_trunks = twilio_Client.trunking.v1.trunks.list()
        trunk = next((t for t in existing_trunks if t.friendly_name == trunk_name), None)

        if not trunk:
            trunk = twilio_Client.trunking.v1.trunks.create(friendly_name=trunk_name)
            logging.info(f"Twilio New SIP trunk -- Trunk SID = {trunk.sid}")
            trunk_sid = trunk.sid
        else:
            trunk_sid = trunk.sid

        # Creating or reusing credential list
        friendly_cred_name = f"{unique_code}_{twilio_number}_credential"
        existing_cred_list = twilio_Client.sip.credential_lists.list()
        existing_cred = next((c for c in existing_cred_list if c.friendly_name == friendly_cred_name), None)

        if existing_cred:
            logging.info(f"Credential list with friendly name: {friendly_cred_name} already exist --> Reusing it")
            credential_list = existing_cred
        else:
            credential_list = twilio_Client.sip.credential_lists.create(friendly_name=friendly_cred_name)
            logging.info(f"Twilio SIP - New credential list created -- CRED SID = {credential_list.sid}")

        # add credentials -- username & password
        try:

            credential_id_pwd = twilio_Client.sip.credential_lists(credential_list.sid).credentials.create(username=unique_code,
                                                                                                           password=unique_code+"PWD94abcxyz")
            logging.info(f"SIP Credential created and added")

            # attach credential list to the SIP trunk with twilio -- twilio sip trunk sid
            cred_sip_attach = twilio_Client.trunking.v1.trunks(trunk_sid).credentials_lists.create(credential_list_sid=credential_list.sid)

        except Exception as e:
            logging.info(f"SIP credential might already exist: {e}")

        # create ip access control list
        ip_acl_friendly_name = f"{unique_code}_{twilio_number}_ip_acl"
        existing_ip_acl = None

        for acl in twilio_Client.sip.ip_access_control_lists.list():
            if acl.friendly_name == ip_acl_friendly_name:
                existing_ip_acl = acl
                break

        if existing_ip_acl:
            logging.info(f"IP ACL with friendly name '{ip_acl_friendly_name}' already exists. Reusing.")
            ip_acl_sid = existing_ip_acl.sid
        else:
            ip_acl_name = twilio_Client.sip.ip_access_control_lists.create(friendly_name=ip_acl_friendly_name)
            logging.info(f"Created new IP ACL -- SID = {ip_acl_name.sid}")
            ip_acl_sid = ip_acl_name.sid

        # Add IP to ACL
        try:
            ip_acl_added = twilio_Client.sip.ip_access_control_lists(ip_acl_name.sid).ip_addresses.create(friendly_name="allIPs",
                                                                                                        ip_address="0.0.0.0", #should be hosted ip
                                                                                                        cidr_prefix_length=1)
            logging.info(f"IP access control list added to the SIP : SID - {ip_acl_added.ip_access_control_list_sid}")

        except Exception as e:
            logging.info(f"IP address may already be added to ACL. Details: {e}")

        # add termination
        termination_uri = f"{trunk_sid}.pstn.twilio.com"
        logging.info(f"Termination URI: {termination_uri}")

        termination = twilio_Client.trunking.v1.trunks(trunk_sid).update(domain_name=termination_uri)
        logging.info(f"Termination URI has been all setup !!! ")

        ret = {
                "trunk_sid": trunk_sid,
                "termination_uri": termination_uri,
                "credential_list_sid": credential_list.sid,
                "sip_username": unique_code,
                "sip_password": unique_code+"PWD94abcxyz"
            }
        
        return ret
    
    except Exception as e:
        logging.info(f"Exception Hit -- Function: setup_twilio_outbound_call -- Error: {e}")

############################################################################################
# Create LiveKit outbound setup
############################################################################################
async def create_livekit_outbound_trunk(twilio_number, termination_uri, sip_username, sip_password, unique_code):
    try:

        async with livekit_client() as lkapi:             
            
            try:
                # checking existing trunk
                existing_trunks = await lkapi.sip.list_sip_outbound_trunk(ListSIPOutboundTrunkRequest())

                for trunk in ((existing_trunks.ListFields()[0])[1]):
                    if trunk.address == termination_uri:
                        logging.info(f"Outbound trunk already exists - SIP TRUNK ID: {trunk.sip_trunk_id}")
                        return {
                            "outbound_sip_trunk_id": trunk.sip_trunk_id,
                            "termination_uri": trunk.address,
                            "sip_username": trunk.auth_username,
                            "sip_password": trunk.auth_password  # Reuse input, as API won't return it
                        }
            except Exception as e:
                logging.info(f"No outbound trunk found that matches our requirements")

            # create outbound trunk info
            outbound_trunk_info = SIPOutboundTrunkInfo(name=f"{unique_code}_{twilio_number}_outbound_info",
                                                    address=termination_uri,
                                                    auth_username=sip_username,
                                                    numbers=[twilio_number],
                                                    auth_password=sip_password)
            logging.info(f"Outbound Trunk info has been created")
            
            create_outbound_request = CreateSIPOutboundTrunkRequest(trunk=outbound_trunk_info)
            logging.info(f"Outbound Trunk request object been created")

            outbound_response = await lkapi.sip.create_sip_outbound_trunk(create=create_outbound_request)
            logging.info(f"Outbound Response : SIP TRUNK ID - {outbound_response.sip_trunk_id}")

            ret = {
                    "outbound_sip_trunk_id": outbound_response.sip_trunk_id,
                    "termination_uri": termination_uri,
                    "sip_username": sip_username,
                    "sip_password": sip_password
                }
            
            return ret
    
    except Exception as e:
        logging.info(f"Exception Hit -- Function: create_livekit_outbound_trunk -- Error: {e}")

############################################################################################
# Create Outbound Call
############################################################################################
async def create_outbound_call(outbound_sip_trunk_id, twilio_number, callee_number, room_name, meeting_id=None,
                               meeting_password=None):
    try:
        async with livekit_client() as lkapi:
            if meeting_id and meeting_password != None:
            # create sip participant request
                sip_participant_request = CreateSIPParticipantRequest(sip_trunk_id=outbound_sip_trunk_id,
                                                                    sip_number=twilio_number,
                                                                    sip_call_to=callee_number,
                                                                    room_name=room_name,
                                                                    participant_identity="zoom",
                                                                    participant_name="zoom_meeting",
                                                                    dtmf=f"wwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwww{meeting_id}#wwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwww{meeting_password}#",
                                                                    play_ringtone=True,
                                                                    krisp_enabled=True)
            else:
            # create sip participant request
                sip_participant_request = CreateSIPParticipantRequest(sip_trunk_id=outbound_sip_trunk_id,
                                                                    sip_number=twilio_number,
                                                                    sip_call_to=callee_number,
                                                                    room_name=room_name,
                                                                    participant_identity="outbound",
                                                                    participant_name="outbound_call",
                                                                    play_ringtone=True,
                                                                    krisp_enabled=True)

            logging.info(f"Attemting a call to: {callee_number}")
            response_call = await lkapi.sip.create_sip_participant(sip_participant_request)
            logging.info(
                f"Call attempted successfully - SIP Call ID: {response_call.sip_call_id} - Participant ID: {response_call.participant_id}")

            ret = {
                "sip_call_id": response_call.sip_call_id,
                "participant_id": response_call.participant_id,
                "status": "call_attempted",
                "called_number": callee_number
            }

            return ret

    except Exception as e:
        logging.info(f"Exception Hit -- Function: create_outbound_call -- Error: {e}")
