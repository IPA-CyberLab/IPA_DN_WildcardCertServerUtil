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
    domainFqdn = Str.NormalizeFqdn(domainFqdn)

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


# 証明書が正しく発行 (更新) されたら、その内容を確認した上で、nginx に適用し提供開始する
def SetupCert(domainFqdn: str):
    domainFqdn = Str.NormalizeFqdn(domainFqdn)

    certDir = os.path.join(
        "/var/ipa_dn_wildcard/issued_certs/", domainFqdn + "/")
    keyFile = os.path.join(certDir, F"{domainFqdn}.key")
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

    # nginx 用に証明書を保存する
    nginxCertFile = F"/var/ipa_dn_wildcard/nginx/sites.d/wildcard_cert_{domainFqdn}.cer"
    nginxKeyFile = F"/var/ipa_dn_wildcard/nginx/sites.d/wildcard_cert_{domainFqdn}.key"
    nginxConfigFile = F"/var/ipa_dn_wildcard/nginx/sites.d/server_{domainFqdn}.conf"
    Lfs.WriteAllText(nginxCertFile, certBody)
    Lfs.WriteAllText(nginxKeyFile, keyBody)

    # nginx 用の追加の config ファイルを生成して保存する
    nginxSiteConfigBody = Str.ReplaceMultiStr("""  
  server {
    listen 80;
    listen [::]:80;
    listen [::]:443 ssl;
    listen 443 ssl;
    
    server_name ssl-cert-server.__FQDN__;
    
    server_tokens off;
    ssl_certificate /etc/nginx/sites.d/wildcard_cert___FQDN__.cer;
    ssl_certificate_key /etc/nginx/sites.d/wildcard_cert___FQDN__.key;
    
    location / {
      root /usr/share/nginx/html/;
      index a.html;
      autoindex on;
      autoindex_exact_size on;
      autoindex_format html;
      autoindex_localtime on;
      auth_basic "Auth requested";
      auth_basic_user_file /etc/nginx/htpasswd.txt;
    }
  }

""", {"__FQDN__": domainFqdn})

    Lfs.WriteAllText(nginxConfigFile, nginxSiteConfigBody)




# メイン処理
if __name__ == '__main__':
    # まず証明書を発行 (更新) する
    #RequestNewCertIssue(DOMAIN_FQDN, TEST_MODE)

    # 証明書が正しく発行 (更新) されたら、その内容を確認した上で、nginx に適用する
    SetupCert(DOMAIN_FQDN)
   
