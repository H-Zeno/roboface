import asyncio
import json
import logging
import os
import uuid

import cv2
import numpy as np
import simpler_env
from aiohttp import web
from aiortc import (
    RTCConfiguration,
    RTCIceServer,
    RTCPeerConnection,
    RTCSessionDescription,
)
from aiortc.mediastreams import MediaStreamError, VideoStreamTrack
from av import VideoFrame
from simpler_env.utils.env.observation_utils import get_image_from_maniskill2_obs_dict

logging.basicConfig(level=logging.INFO)
ROOT = os.path.dirname(os.path.dirname(__file__))
pcs = set()


class VideoTransformTrack(VideoStreamTrack):
    """
    A video stream track that transforms frames from the simulation.
    """

    kind = "video"

    def __init__(self):
        super().__init__()  # don't forget this!
        self._queue = asyncio.Queue()

    async def recv(self):
        frame = await self._queue.get()
        if frame is None:
            raise MediaStreamError()

        pts, time_base = await self.next_timestamp()
        frame.pts = pts
        frame.time_base = time_base
        return frame

    def stop(self):
        super().stop()
        self._queue.put_nowait(None)


async def index(request):
    content = open(os.path.join(ROOT, "frontend/index.html"), "r").read()
    return web.Response(content_type="text/html", text=content)


async def offer(request):
    params = await request.json()
    offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])

    config = RTCConfiguration(
        iceServers=[
            RTCIceServer("stun:stun.l.google.com:19302"),
            RTCIceServer("stun:stun1.l.google.com:19302"),
        ]
    )
    pc = RTCPeerConnection(configuration=config)
    pc_id = "PeerConnection(%s)" % uuid.uuid4()
    pcs.add(pc)

    def log_info(msg, *args):
        logging.info(pc_id + " " + msg, *args)

    log_info("Created for %s", request.remote)

    # prepare local media
    player = VideoTransformTrack()
    pc.addTrack(player)
    pc.simulation_task = asyncio.create_task(run_simulation(player))

    @pc.on("datachannel")
    def on_datachannel(channel):
        @channel.on("message")
        def on_message(message):
            if isinstance(message, str) and message.startswith("ping"):
                channel.send("pong" + message[4:])

    @pc.on("iceconnectionstatechange")
    async def on_iceconnectionstatechange():
        log_info("ICE connection state is %s", pc.iceConnectionState)
        if pc.iceConnectionState in ["failed", "closed"]:
            if hasattr(pc, "simulation_task"):
                pc.simulation_task.cancel()
            await pc.close()
            pcs.discard(pc)

    @pc.on("track")
    def on_track(track):
        log_info("Track %s received", track.kind)

        @track.on("ended")
        async def on_ended():
            log_info("Track %s ended", track.kind)
            # The simulation is tied to the peer connection, not an individual
            # track so we don't need to cancel it here. It will be cancelled
            # when the ice connection state changes to failed or closed.
            player.stop()

    # handle offer
    await pc.setRemoteDescription(offer)

    # send answer
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    return web.Response(
        content_type="application/json",
        text=json.dumps(
            {"sdp": pc.localDescription.sdp, "type": pc.localDescription.type}
        ),
    )


async def on_shutdown(app):
    # close peer connections
    coros = [pc.close() for pc in pcs]
    await asyncio.gather(*coros)
    pcs.clear()


def blocking_run_simulation(loop, player):
    """
    This function runs in a separate thread and executes the blocking
    simulation steps.
    """
    env = simpler_env.make("google_robot_pick_coke_can")
    obs, reset_info = env.reset()
    instruction = env.get_language_instruction()
    print("Reset info", reset_info)
    print("Instruction", instruction)

    done, truncated = False, False
    while not (done or truncated):
        image = get_image_from_maniskill2_obs_dict(env, obs)

        # # a temporary fix for the issue of the image being in BGR format
        # image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        # Manually construct the VideoFrame
        frame = VideoFrame.from_ndarray(image, format="rgb24")

        # Safely put the frame in the queue from the separate thread
        loop.call_soon_threadsafe(player._queue.put_nowait, frame)

        action = env.action_space.sample()
        obs, reward, done, truncated, info = env.step(action)
        new_instruction = env.get_language_instruction()
        if new_instruction != instruction:
            instruction = new_instruction
            print("New Instruction", instruction)

    episode_stats = info.get("episode_stats", {})
    print("Episode stats", episode_stats)
    loop.call_soon_threadsafe(player.stop)


async def run_simulation(player):
    """
    This async function prepares the event loop and runs the blocking
    simulation in a separate thread to avoid blocking the asyncio event loop.
    """
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, blocking_run_simulation, loop, player)


if __name__ == "__main__":
    app = web.Application()
    app.on_shutdown.append(on_shutdown)
    app.router.add_get("/", index)
    app.router.add_post("/offer", offer)
    web.run_app(app, host="0.0.0.0", port=4040)
