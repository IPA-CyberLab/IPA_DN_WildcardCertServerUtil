# Copyright (c) 2021- IPA CyberLab.
# All Rights Reserved.
#
# Author: Daiyuu Nobori
# 1. Let's Encrypt のワイルドカード証明書の発行認証を行なうための TXT レコード応答用 Docker を Linux 上で立ち上げる。
# 2. Let's Encrypt のワイルドカード証明書の発行認証を要求し、認証を成功させる。
# 3. 発行された Let's Encrypt のワイルドカード証明書のファイルを整理し、指定したディレクトリに設置する。

import os
import json
import subprocess
import inspect
from typing import List, Tuple, Dict, Set
import typing
from datetime import timedelta, tzinfo, timezone, time, date, datetime
import time as systime

from submodules.IPA_DN_PyNeko.v1.PyNeko import *

DOMAIN_FQDN = "wctest1.dnobori.jp"

TEST_MODE = True

# 認証用 DNS サーバーコンテナがすでに作成されていれば停止して削除する
def StopDnsServerContainer():
    # 認証用 DNS サーバーコンテナがすでに作成されているかどうか
    if Docker.IsContainerExists("dnsserver"):
        # すでに作成されているのでコンテナを停止する
        Print("The container 'dnsserver' still exists. Deleting it.")

        try:
            Docker.StopContainer("dnsserver")
            Print("The container 'dnsserver' stopped.")
        except:
            pass

        try:
            Docker.DeleteContainer("dnsserver")
            Print("The container 'dnsserver' deleted.")
        except:
            pass

# 証明書の発行をリクエストする
def RequestNewCertIssue(domainFqdn: str, testMode: bool):
    # 認証用 DNS サーバーコンテナがすでに起動していれば停止する
    StopDnsServerContainer()

    # 認証用 DNS サーバーコンテナを起動する
    # このコンテナはバックグラウンドで起動されたままになる
    Print("Starting the container 'dnsserver' ...")

    Docker.RunDockerCommandInteractive(
        "run --rm -d --name dnsserver -p 53:53/udp -p 127.0.0.1:88:80 dockervault.dn.ipantt.net/dockervault-cunnie-wildcard-dns-http-server:20210602_001".split()
    )

    Print("The container 'dnsserver' running OK.")


    # acme.sh コンテナを実行し Let's Encrypt から証明書を取得する
    try:
        Print("Starting the acme.sh container ...")

        Docker.RunDockerCommandInteractive(
            f"run --rm -it -v /var/ipa_dn_wildcard/issued_certs/:/acme.sh/ -e ACMEDNS_UPDATE_URL=http://127.0.0.1:88/update --net=host dockervault.dn.ipantt.net/dockervault-neilpang-acme-sh:20210602_001 --issue --insecure --days 30 --dnssleep 1 --debug -d {domainFqdn} -d *.{domainFqdn} {'--test --force' if testMode else ''} --dns dns_acmedns".split(
            )
        )

        Print("The cert issue process by acme.sh container  OK.")
    finally:
        # 認証用 DNS サーバーコンテナを停止する
        StopDnsServerContainer()


while True:
    print(Time.FloatTick64())
    Time.Sleep(1000)
    

print(systime.perf_counter_ns())
systime.sleep(1)
print(systime.perf_counter_ns())
systime.sleep(1)
print(systime.perf_counter_ns())


utcnow = Time.UtcNow()
print(utcnow)
ms = Time.ToTime64(utcnow)
print(ms)
print(Time.FromTime64(ms))

localnow = Time.LocalNow()
print(localnow)
ms = Time.ToTime64(localnow)
print(ms)
print(Time.FromTime64(ms, True))

localnow = Time.ToLocal(localnow)
print(localnow)

print(datetime.now())
print(Time.ToLocal(datetime.now()))
print(Time.ToLocal(Time.ToLocal(datetime.now())))
print(Time.ToUtc(Time.ToLocal(datetime.now())))



exit(0)

# メイン処理
if __name__ == '__main__':
    # まず証明書を発行 (更新) する
    #RequestNewCertIssue(DOMAIN_FQDN, TEST_MODE)

    # 証明書が正しく発行 (更新) されたら、その内容を確認する
    certDir = os.path.join("/var/ipa_dn_wildcard/issued_certs/", DOMAIN_FQDN + "/")
    keyFile = os.path.join(certDir, F"{DOMAIN_FQDN}.key")
    certFile = os.path.join(certDir, "fullchain.cer")

    Print(F"Checking the '{keyFile}' contents...")
    certBody = Lfs.ReadAllText(certFile)
    if not Str.InStr(certBody, "-----BEGIN CERTIFICATE-----", caseSensitive=True):
        raise Err(F"The issued cert file '{certFile}' has invalid format.")

    Print(F"Checking the '{certFile}' contents...")
    keyBody = Lfs.ReadAllText(keyFile)
    if not Str.InStr(keyBody, "-----BEGIN RSA PRIVATE KEY-----", caseSensitive=True):
        raise Err(F"The issued key file '{keyFile}' has invalid format.")
    
    Print("Issued cert files are OK.")

    



