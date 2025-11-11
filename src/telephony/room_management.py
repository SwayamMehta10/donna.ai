import asyncio
from dotenv import load_dotenv
import os
import logging
import json
import sys
import uuid
from src.utils.mylogger import logging
from livekit import api
from livekit.api import ListRoomsRequest, DeleteRoomRequest
from livekit.protocol.sip import ListSIPInboundTrunkRequest

from livekit.api import (
    CreateRoomRequest,
    ListRoomsRequest,
    CreateAgentDispatchRequest,
    RoomCompositeEgressRequest,
    S3Upload,
    SegmentedFileOutput,
    EncodedFileOutput,
    EncodedFileType,
    AccessToken,
    RoomAgentDispatch,
    RoomConfiguration,
    VideoGrants,    
)

# Load environment variable
load_dotenv()

# Generate room token
def create_token_with_agent_dispatch(room_name, agent_name, metadata) -> str:
    token = (
        AccessToken(api_key=os.getenv("LIVEKIT_API_KEY"), api_secret=os.getenv("LIVEKIT_API_SECRET"))
        .with_identity(str(uuid.uuid4()))
        .with_grants(VideoGrants(room_join=True, room=room_name))
        .with_room_config(
            RoomConfiguration(
                agents=[
                    RoomAgentDispatch(agent_name=agent_name, metadata=metadata)
                ],
            ),
        )
        .to_jwt()
    )
    return token

# Create a room and dispatch the agent
async def manage_room(full_user_config, agent_name) -> str:
    """Creates the room and dispatches the agent into the room

    Args:
        full_user_config (dict): users configuration for Voice Bot

    Returns:
        str: room token
    """

    logging.info(f"Room Management: full_user_config type: {type(full_user_config)}")
    # Create livekit API
    lkapi = api.LiveKitAPI(
        url=os.getenv("LIVEKIT_URL"),
        api_key=os.getenv("LIVEKIT_API_KEY"),
        api_secret=os.getenv("LIVEKIT_API_SECRET")
    )    
    # full_user_config = json.loads(full_user_config_json)
    try:

        # create unique room name
        if full_user_config.get("room_name") is None:
            room_name = f"room_{uuid.uuid4().hex[:8]}_{full_user_config.get('project_id')}"
            full_user_config.update({
                "room_name": room_name
            })

        agent_name = agent_name
        session_id= uuid.uuid4().hex[:20]
        # add room_name and agent_name into full_user_config
        full_user_config.update({
            "agent_name": agent_name,
            "session_id": session_id
        })
        
        logging.info(f"Room Management: full_user_config type after room name and agent name: {type(full_user_config)}")
        logging.info(f"Room Management: full_user_config after room name and agent name: {full_user_config}")

        # Create unique name of the room and set full_user_config as room metadata - check if user wants voice to be stored or not

        room = await lkapi.room.create_room(CreateRoomRequest(
            name=full_user_config.get("room_name")
        ))
        logging.info(f"Room: {full_user_config.get('room_name')} created without voice recording")


        logging.info(f"Room: {full_user_config.get('room_name')} created successfully")

        # Dispatch agent using API
        dispatch = await lkapi.agent_dispatch.create_dispatch(CreateAgentDispatchRequest(
            room=full_user_config.get("room_name"),
            agent_name=full_user_config.get("agent_name"),
            metadata=json.dumps(full_user_config, indent=2)
        ))
        logging.info(f"Agent dispatch response: {dispatch}")
        logging.info(f"Agent ID: {dispatch.id}")

        
        # Generate room access tokens 
        room_token = create_token_with_agent_dispatch(room_name=room.name, agent_name=full_user_config.get("agent_name"), metadata=json.dumps(full_user_config, indent=2))
        logging.info(f"Room Access Token: {room_token}")

        
        print(room_token)
        return room_token
    
    except Exception as e:
        logging.info(f"Exception triggered: Function -> manage_room \nError: {e} ")
        raise Exception(e, sys)
    
    finally:
        
        await lkapi.aclose()

# # Get room metadata explicitly
async def get_room_metadata(room_name):

    try:
        logging.info(f"Room Name Type: {type(room_name)}")
        lkapi = api.LiveKitAPI(url=os.getenv("LIVEKIT_URL"),
                       api_key=os.getenv("LIVEKIT_API_KEY"),
                       api_secret=os.getenv("LIVEKIT_API_SECRET"))
    
        existing_room = await lkapi.room.list_rooms(ListRoomsRequest(names=[room_name]))
        for room in existing_room.rooms:
            metadata = json.loads(room.metadata)

        return metadata
    
    except Exception as e:
        logging.info(f"Exception hit -> Function: get_room_metadata -> Error: {e} ")

        return {}
    
    finally:
        await lkapi.aclose()

############################################################################################
async def get_sip_metadata(room_name):

    lst = room_name.split("_")
    trunk_name = lst[0]+"_LK_inboundTrunk"

    try:
        lkapi = api.LiveKitAPI(url=os.getenv("LIVEKIT_URL"),
                       api_key=os.getenv("LIVEKIT_API_KEY"),
                       api_secret=os.getenv("LIVEKIT_API_SECRET"))
    
        existing_trunks = await lkapi.sip.list_sip_inbound_trunk(ListSIPInboundTrunkRequest())


        for trunk in ((existing_trunks.ListFields()[0])[1]):
            if trunk.name == trunk_name:
                metadata = trunk.metadata

        return json.loads(metadata)
    
    except Exception as e:
        logging.info(f"Exception hit -> Function: get_room_metadata -> Error: {e} ")

        return {}
    
    finally:
        await lkapi.aclose()
        
############################################################################################
# cleanup the room and other process
async def delete_lk_room(room_name):
    try:
        lkapi = api.LiveKitAPI(url=os.getenv("LIVEKIT_URL"),
                       api_key=os.getenv("LIVEKIT_API_KEY"),
                       api_secret=os.getenv("LIVEKIT_API_SECRET"))
    
        await lkapi.room.delete_room(DeleteRoomRequest(room=room_name))
    
    except Exception as e:
        logging.info(f"Exception hit -> Function: get_room_metada -> Error: {e} ")

        return {}
    
    finally:
        await lkapi.aclose()

############################################################################################
############################################################################################
# cancel running tasks
async def clear_running_tasks():
    running_tasks = asyncio.all_tasks()
    logging.info(f"Currently running tasks: {len(running_tasks)}")

    for task in running_tasks:
        if task is not asyncio.current_task():
            logging.info(f"Cancelling Task: {task.get_name()} -> Status: {task._state}")
            task.cancel()

############################################################################################

if __name__ == "__main__":
    
    full_user_config = json.loads(sys.argv[1])

    asyncio.run(manage_room(full_user_config))


            
        

