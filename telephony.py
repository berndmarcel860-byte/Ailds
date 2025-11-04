# -*- coding: utf-8 -*-
import time, json, requests
from pathlib import Path

class Telephony:
    def __init__(self, host: str, port: int, user: str, pwd: str, app: str):
        self.host=host; self.port=port; self.user=user; self.pwd=pwd; self.app=app
        self.sess=requests.Session()
        self.sess.auth=(user,pwd)
        self.sess.headers.update({"User-Agent":"AI-Agent/1.0"})

    def _url(self, path: str) -> str:
        return f"http://{self.host}:{self.port}{path}"

    def channel_alive(self, ch: str) -> bool:
        try:
            r=self.sess.get(self._url(f"/ari/channels/{ch}"), timeout=3)
            return r.ok
        except:
            return False

    def play(self, ch: str, media: str) -> bool:
        r=self.sess.post(self._url(f"/ari/channels/{ch}/play"), params={"media":media}, timeout=10)
        return r.ok

    def record(self, ch: str, name: str, max_sec: int, silence_sec: float):
        p={"name":name,"format":"wav","maxDurationSeconds":max_sec,"maxSilenceSeconds":silence_sec,
           "ifExists":"overwrite","beep":"false","terminateOn":"none"}
        self.sess.post(self._url(f"/ari/channels/{ch}/record"), params=p, timeout=10)

    def hangup(self, ch: str):
        try:
            self.sess.delete(self._url(f"/ari/channels/{ch}"), timeout=5)
        except: pass

    def wait_for_playback_finish(self, ws, timeout=20.0):
        start=time.time()
        while time.time()-start<timeout:
            try:
                ev=json.loads(ws.recv())
                if ev.get("type") in ("PlaybackFinished","PlaybackStopped"):
                    return True
                if ev.get("type") in ("ChannelHangupRequest","StasisEnd"):
                    return False
            except:
                break
        return True
