#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 
# Copyright (c) 2021- IPA CyberLab.
# All Rights Reserved.
#
# Author: Daiyuu Nobori
# 
# 2021/06/02 に生まれて初めて書いたインチキ Python スクリプト！！
# 
# 処理の内容
# 1. Let's Encrypt のワイルドカード証明書の発行認証を行なうための TXT レコード応答用 Docker を Linux 上で立ち上げる。
# 2. Let's Encrypt のワイルドカード証明書の発行認証を要求し、認証を成功させる。
# 3. 発行された Let's Encrypt のワイルドカード証明書のファイルを整理し、指定したディレクトリに設置する。

import os
import json
import subprocess
import inspect
import typing
import time as systime
import argparse
from typing import List, Tuple, Dict, Set, Callable, TypeVar, Type
from datetime import timedelta, tzinfo, timezone, time, date, datetime

from submodules.IPA_DN_PyNeko.v1.PyNeko import *



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
def RequestNewCertIssue(domainFqdn: str, testMode: bool, forceMode: bool):
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
            f"run --rm -i -v /var/ipa_dn_wildcard/issued_certs/:/acme.sh/ -e ACMEDNS_UPDATE_URL=http://127.0.0.1:88/update --net=host dockervault.dn.ipantt.net/dockervault-neilpang-acme-sh:20210602_001 --issue --insecure --days 30 --dnssleep 1 --debug -d {domainFqdn} -d *.{domainFqdn} {'--test' if testMode else ''} {'--force' if forceMode else ''} --dns dns_acmedns".split(
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

    csrFile = os.path.join(certDir, F"{domainFqdn}.csr")
    csrBody = Lfs.ReadAllText(csrFile)

    certConfFile = os.path.join(certDir, F"{domainFqdn}.conf")
    certConfBody = Lfs.ReadAllText(certConfFile)

    Print(F"Checking the '{certFile}' contents...")
    certBody = Lfs.ReadAllText(certFile)
    if not Str.InStr(certBody, "-----BEGIN CERTIFICATE-----", caseSensitive=True):
        raise Err(F"The issued cert file '{certFile}' has invalid format.")

    Print(F"Checking the '{keyFile}' contents...")
    keyBody = Lfs.ReadAllText(keyFile)
    if not Str.InStr(keyBody, "-----BEGIN RSA PRIVATE KEY-----", caseSensitive=True):
        raise Err(F"The issued key file '{keyFile}' has invalid format.")

    Print("Issued cert files are OK.")

    # .p12 ファイルを生成する
    pfxFile = os.path.join("/tmp/", F"_tmp_{domainFqdn}.pfx")
    EasyExec.Run(
        F"openssl pkcs12 -export -in {certFile} -inkey {keyFile} -out {pfxFile} -passout pass:".split(),
        shell=False,
        timeoutSecs=15)
    
    pfxBody = Lfs.ReadAllData(pfxFile)

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
    
    server_name __FQDN__ www.__FQDN__ ssl-cert-server.__FQDN__;
    
    server_tokens off;
    ssl_certificate /etc/nginx/sites.d/wildcard_cert___FQDN__.cer;
    ssl_certificate_key /etc/nginx/sites.d/wildcard_cert___FQDN__.key;
    
    location / {
      root /usr/share/nginx/html/;
      index __dummy_file__.html;
      autoindex on;
      autoindex_exact_size on;
      autoindex_format html;
      autoindex_localtime on;
    }

    location /wildcard_cert_files/ {
      alias /usr/share/nginx/html/wildcard_cert_files/;
      index __dummy_file__.html;
      autoindex on;
      autoindex_exact_size on;
      autoindex_format html;
      autoindex_localtime on;
      auth_basic "Auth requested";
      auth_basic_user_file /etc/nginx/htpasswd.txt;
    }
  }

""", {"__FQDN__": domainFqdn})

    # server config の保存
    Lfs.WriteAllText(nginxConfigFile, nginxSiteConfigBody)

    # コンテンツ (証明書ファイル) の保存
    now = Time.NowLocal()
    wwwRoot = "/var/ipa_dn_wildcard/wwwroot/wildcard_cert_files/"
    certRoot = os.path.join(wwwRoot, domainFqdn)
    yymmddRoot = os.path.join(certRoot, Time.ToYYYYMMDD_HHMMSS(now))
    latestRoot = os.path.join(certRoot, "latest")

    timestampBody = Time.ToYYYYMMDD_HHMMSS(now) + Str.NEWLINE_LF

    Lfs.WriteAllText(os.path.join(yymmddRoot, "cert.cer"), certBody)
    Lfs.WriteAllText(os.path.join(yymmddRoot, "cert.key"), keyBody)
    Lfs.WriteAllText(os.path.join(yymmddRoot, "cert.conf"), certConfBody)
    Lfs.WriteAllText(os.path.join(yymmddRoot, "cert.csr"), csrBody)
    Lfs.WriteAllData(os.path.join(yymmddRoot, "cert.pfx"), pfxBody)
    Lfs.WriteAllText(os.path.join(yymmddRoot, "timestamp.txt"), timestampBody)

    Lfs.WriteAllText(os.path.join(latestRoot, "cert.cer"), certBody)
    Lfs.WriteAllText(os.path.join(latestRoot, "cert.key"), keyBody)
    Lfs.WriteAllText(os.path.join(latestRoot, "cert.conf"), certConfBody)
    Lfs.WriteAllText(os.path.join(latestRoot, "cert.csr"), csrBody)
    Lfs.WriteAllData(os.path.join(latestRoot, "cert.pfx"), pfxBody)
    Lfs.WriteAllText(os.path.join(latestRoot, "timestamp.txt"), timestampBody)

    # ipa_dn_wildcard_ngnix という名前の Docker を再起動
    Docker.RestartContainer("ipa_dn_wildcard_ngnix")




# メイン処理
if __name__ == '__main__':
    src = Lfs.ReadAllText("./test.cer")
    res = Util.GetSingleHostCertAndIntermediateCertsFromCombinedCert(src)
    Lfs.WriteAllText("./1.cer", res[0])
    Lfs.WriteAllText("./2.cer", res[1])
    Lfs.WriteAllText("./3.cer", res[2])
    exit()
    # 引数解析
    parser = argparse.ArgumentParser()
    parser.add_argument("domain_fqdn", metavar="<Domain FQDN>", type=str, help="Specify domain fqdn (e.g. abc.example.org)")
    parser.add_argument("--test", action="store_true", help="Test mode (use Let's encrypt staging server)")
    parser.add_argument("--force", action="store_true",
                        help="Force mode (Renew cert forcefully regardless the expires date)")
    parser.add_argument("--copyonly", action="store_true",
                        help="Do not renew certificates. Copy only. (for debug)")

    args = parser.parse_args()
    domainFqdn: str = args.domain_fqdn
    testMode: bool = args.test
    forceMode: bool = args.force
    copyonly: bool = args.copyonly

    # まず証明書を発行 (更新) する
    # なお、更新の必要がない場合 (有効期限がまだまだある) は、ここで例外が発生し、これ以降の処理は実施されない
    if not copyonly:
        RequestNewCertIssue(domainFqdn, testMode, forceMode)

    # 証明書が正しく発行 (更新) されたら、その内容を確認した上で、nginx に適用する
    SetupCert(domainFqdn)
   
