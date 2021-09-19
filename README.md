# IPA_DN_WildcardCertServerUtil (Python で書かれた Let's Encrypt ワイルドカード DNS 用証明書自動更新・証明書ファイル提供サーバー)
作成: 登 大遊 (Daiyuu Nobori)


## 目的
本プログラム (IPA_DN_WildcardCertServerUtil) は、IPA_DN_WildCardDnsServer (Go 言語で書かれたステートレスなワイルドカード DNS サーバー, https://github.com/IPA-CyberLab/IPA_DN_WildCardDnsServer/) と連携して動作させることが可能な、Let's Encrypt に対応したワイルドカード SSL 証明書 (例: `*.example.org`) を定期的に更新し続け、更新された最新の証明書を nginx ベースの Web サーバーで Basic 認証を施した上で同じ組織内の他のサーバーに対して安定して提供するための Web サーバーユーティリティである。

- 本ユーティリティは、IPA_DN_WildCardDnsServer (Go 言語で書かれたステートレスなワイルドカード DNS サーバー, https://github.com/IPA-CyberLab/IPA_DN_WildCardDnsServer/) と連携して動作させることを「手法 1」としている。ワイルドカード DNS の概念と使い方の主な説明、および DNS サーバーのインストール・稼働方法は、https://github.com/IPA-CyberLab/IPA_DN_WildCardDnsServer/ のほうに記載しているので、そちらを参照すること。

- なお、「手法 2」として、IPA_DN_WildCardDnsServer を使用せず、通常の DNS サーバー (例: BIND, Microsoft DNS, PowerDNS, NSD, AWS Route 53、その他の各種の DNS サービスプロバイダの DNS サーバー) で DNS ドメインのゾーンを運営している場合も、本プログラムを利用することは可能である。詳しくは、下記の説明のとおりである。

# インストールマニュアル
以下の説明では、本プログラムを `example.org` というドメインで使用する場合を例示している。この `example.org` という文字列を、実際に運用したいドメイン名に置換して解釈すること。


## 必要なもの
事前に必要なものは、以下のとおりである。
- 本プログラムによって運用したいドメイン名 1 個  
  (上記の説明における `example.org` に相当するもの。サブドメインでもよい。)
- 上記のドメインの DNS 権威サーバーが適切に設定され、本 IPA_DN_WildcardCertServerUtil プログラムを動作させる 1 台の DNS 更新・証明書ファイル提供サーバーを指す A レコードを示す `_acme-challange.example.org` という名前の NS レコードが適切に設定されている状態。これは、以下の 2 つの方法のいずれかによって実現可能である。
  - (手法 1) 上記のドメインが IPA_DN_WildCardDnsServer (Go 言語で書かれたステートレスなワイルドカード DNS サーバー, https://github.com/IPA-CyberLab/IPA_DN_WildCardDnsServer/) によってすでに運用されている状態
  (すなわち、IPA_DN_WildCardDnsServer のために 2 台の VM が動作している状態であること)
  - (手法 2) IPA_DN_WildCardDnsServer を使用せず、通常の DNS サーバー (例: BIND, Microsoft DNS, PowerDNS, NSD, AWS Route 53、その他の各種の DNS サービスプロバイダの DNS サーバー) で DNS ドメインのゾーンを運営している場合は、その DNS 権威サーバーにおいて、本 IPA_DN_WildcardCertServerUtil プログラムを動作させる 1 台の DNS 更新・証明書ファイル提供サーバーを指す A レコードを示す `_acme-challange.example.org` という名前の NS レコードを適切に設定すること。ここで、NS レコードというものは、ホスト名を指定するものであるため、IPv4 アドレスを直接指定することはできない。まず、A レコードとして、たとえば `ssl-cert-server.example.org` というような名前のレコードを定義し、ここに本サーバーの IPv4 アドレスを記載するべきである。次に、NS レコードとして、`_acme-challange.example.org` というレコード名を定義し、これの NS の値として `ssl-cert-server.example.org` というような名前の先ほど定義した A レコードを指定するべきである。
- この IPA_DN_WildcardCertServerUtil の Web サーバーのために、1 台の VM が必要である。これは、現代的な Linux が動作する任意のクラウドまたはオンプレミスの VM であって、固定グローバル IPv4 アドレスの割当てがされているものであれば、何でも構わない。
  - Linux のバージョンは、Ubuntu 20.04 または Ubuntu 18.04 を推奨する。それ以外の Linux でもおおむね動作すると思われるが、自己責任で動作させること。
  - この IPA_DN_WildcardCertServerUtil の Web サーバーの VM は、1 台で差し支え無い。なぜならば、この Web サーバーがダウンしたとしても、DNS 名前解決に影響はなく、単に Let's Encrypt の定期的な証明書の更新ができなくなるためである。以下のサンプルでは、Let's Encrypt の証明書更新は、毎日 1 回証明書の残り有効期限をチェックし、証明書の残り有効期限が 60 日未満になる度に更新を要求する。そこで、もしこの Web サーバーが運悪くしばらくの間ダウンしたとしても、そのダウン期間が 60 日未満であれば、その後 Web サーバーを復旧すれば再度その時点で証明書の更新がなされるので、重大な問題は起こらない。
  - ただし、留意点として、本 Web サーバーから定期的に証明書および秘密鍵ファイルをダウンロードするよう構成されたクライアント (つまり、証明書を利用したい Web サーバーや WebSocket プログラム等) は、本 Web サーバーが停止中は証明書のダウンロードができない。したがって、これらの呼び出し元プログラムは、本 Web サーバーから取得した証明書をローカルで必ずキャッシュするようにしておき、本 Web サーバーへのアクセスが失敗した場合はローカルのキャッシュを使用するようなプログラムにしておく必要がある。
  - なお、定期的に本 Web サーバーの証明書が更新されているかどうかの識別をし、更新されている場合はダウンロードとローカルのプログラムへの適用を行ないたいと考える場合は、証明書のファイルと共に設置されているシンプルなテキストファイルである `timestamp.txt` に証明書発行時のタイムスタンプが `20210606_180016` のように記載されているため、この値が変化しているかどうかをチェックすればよい。


## AWS インスタンスの作成 (AWS を利用する場合)
このマニュアルでは、1 台の VM として、以下を用意するものとして説明を行なう。
```
Amazon EC2 の最も安価な VM インスタンス 1 台 (注意: x64 に限る)
2021/06/06 時点では、「t3a.nano」インスタンス (x64 CPU, RAM 0.5GB) が最もランニングコストが安価である。
これは 0.0047 USD / 時間 (例: 米オレゴンまたは米バージニア北部の DC を選択した場合) のため、1 ドル 120 円として、1 ヶ月あたり 420 円で 1 台の VM を運用することができる。
一方、東京の DC の場合は、0.0061 USD / 時間のため、1 ヶ月あたり 545 円で 1 台の VM を運用することができる。
上記の EC2 コストは、コンピューティングコストであり、ストレージやネットワークは別途課金が発生する可能性があるため注意すること。また、最新のコストは AWS の Web サイトを確認すること。
```


この 1 台の VM は、以下のような設定で作成する。
```
AMI: Ubuntu Server 20.04 LTS (HVM), SSD Volume Type - 64 ビット (x86)
インスタンスタイプ: t3a.nano
ネットワークのセキュリティグループ: SSH (TCP 22)、DNS (UDP 53)、HTTP (TCP 80)、HTTPS (TCP 443)、ICMP IPv4 (楽しみのため) のみを任意のソース IP から通す。
Elastic IP をそれぞれの VM 用に作成し、各 VM に固定で関連付ける。
```


## VM の設定 (SSH 経由)
この 1 台の VM を、SSH 経由で以下のように設定する。

まず、作成したばかりの EC2 サーバーに、ユーザー `ubuntu` として SSH サーバーにログインする。

```
# タイムゾーンを日本標準時 (Asia/Tokyo) に設定する
sudo timedatectl set-timezone Asia/Tokyo

# 最近の Ubuntu はヘンなローカル DNS プロキシが動作しており、けしからん。
# これらを以下のように停止するのである。
sudo systemctl disable systemd-resolved
sudo systemctl stop systemd-resolved
sudo rm /etc/resolv.conf

# すると resolv.conf がなくなってしまうので、
# インチキ Google Public DNS サーバーをひとまず手動で設定する。
echo nameserver 8.8.8.8 | sudo tee /etc/resolv.conf

# 上記を設定すると、Linux が sudo するたびに
# sudo: unable to resolve host ip-xxx-xxx-xxx-xxx: Name or service not known
# などと言ってくるようになりうっとおしいので、
# /etc/hosts に自ホストを追記して解決する。
echo $(ip route get 8.8.8.8 | cut -d " " -f 7 | head -n 1) $(hostname) | sudo tee -a /etc/hosts

# apt-get でいやないやな Docker と apache2-utilsをインストールする。
# apache2-utils をインストールする理由は、htpasswd コマンド を利用したいためである。
sudo apt-get -y update && sudo apt-get -y install docker.io apache2-utils

# ヘンな関係ディレクトリを作成する。
sudo mkdir -p /var/ipa_dn_wildcard/nginx/
sudo mkdir -p /var/ipa_dn_wildcard/nginx/sites.d/
sudo mkdir -p /var/ipa_dn_wildcard/wwwroot/
sudo mkdir -p /var/ipa_dn_wildcard/wwwroot/wildcard_cert_files/

# 以下の手順で nginx に TLS SNI ベースの virtual host が作成され、そこでは Let's Encrypt の SSL 証明書が設定されるが、
# デフォルトのダミー証明書として何か 1 つ SSL 証明書が必要なので、
# インチキ・ダミー証明書をダウンロードしてくる。
# まったく、けしからんことである。
# (これは、登が生成したインチキ証明書である。)
sudo curl http://stable1.dn.ipantt.net/d/210604_001_dummy_certs_94753/00_DummyCert.cer -o /var/ipa_dn_wildcard/nginx/default.crt
sudo curl http://stable1.dn.ipantt.net/d/210604_001_dummy_certs_94753/00_DummyCert.key -o /var/ipa_dn_wildcard/nginx/default.key

# ユーザー名「user123」、パスワード「pass123」という名前で
# nginx Web サーバーの Basic 認証のパスワードを設定する。
# 実運用サーバーにおいては、これらを別のユーザー名とパスワードに変更するべき
# である。この秘密情報を知っている人 (プログラム) だけが、HTTPS 経由で
# 本 Web サーバーにアクセスし、最新の証明書と秘密鍵ファイルをダウンロードできる
# のである。
htpasswd -Bbn user123 pass123 | sudo dd of=/var/ipa_dn_wildcard/nginx/htpasswd.txt


# nginx の設定ファイルを初期化する。この設定ファイルは実際には Docker でマウントされて使用されるのである。
# (少し長いが、EOF の部分までコピーペーストして SSH で一気に貼り付けること。)

sudo dd of=/var/ipa_dn_wildcard/nginx/nginx.conf <<\EOF
user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log notice;
pid /var/run/nginx.pid;
events {
  worker_connections 1024;
  multi_accept on;
  use epoll;
}

http {
  default_type application/octet-stream;
  log_format main '[$time_local] Client=[$remote_addr]:$remote_port Server=[$server_addr]:$server_port Host=$host Proto=$server_protocol Request="$request" Status=$status Size=$body_bytes_sent Referer="$http_referer" UserAgent="$http_user_agent" Username=$remote_user Ssl=$ssl_protocol Cipher=$ssl_cipher';
  access_log /var/log/nginx/access.log main;
  
  limit_req_zone $binary_remote_addr zone=one:64m rate=40r/m;
  limit_req zone=one burst=20 nodelay;
  
  tcp_nopush on;
  tcp_nodelay on;
  sendfile on;
  keepalive_timeout 65;

  server_names_hash_bucket_size 128;
  
  ssl_protocols TLSv1 TLSv1.1 TLSv1.2 TLSv1.3;
  ssl_prefer_server_ciphers on;
  gzip off;
  
  types {
    text/plain cer csr conf key txt;
  }
  
  server {
    listen 80 default_server;
    listen [::]:80 default_server;
    listen 443 ssl default_server;
    listen [::]:443 ssl default_server;
    
    server_name dummy;
    
    server_tokens off;
    ssl_certificate /etc/nginx/default.crt;
    ssl_certificate_key /etc/nginx/default.key;
    
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
  
  include /etc/nginx/sites.d/*.conf;
}
EOF

# Docker を用いて nginx サーバーを起動する。
# これにより、Web サーバーは、Linux 起動後に自動起動するようになる。
sudo docker run -d --restart always --name ipa_dn_wildcard_ngnix --mount type=bind,source=/var/ipa_dn_wildcard/nginx/,target=/etc/nginx/,readonly --mount type=bind,source=/var/ipa_dn_wildcard/wwwroot/,target=/usr/share/nginx/html/,readonly -p 80:80 -p 443:443 dockervault.dn.ipantt.net/dockervault-nginx-alpine-x64:20210604_001

# 糸冬了！！
```


## DNS サーバー側の IP アドレスの設定 (IPA_DN_WildCardDnsServer を使用している場合)
すでに稼働している IPA_DN_WildCardDnsServer (Go 言語で書かれたステートレスなワイルドカード DNS サーバー, https://github.com/IPA-CyberLab/IPA_DN_WildCardDnsServer/) の `config.go` の以下の設定行の IPv4 アドレスを、本 VM サーバーのグローバル固定 IPv4 アドレスに変更する。

```
cfg.WildcardCertServerIp =    "x.y.z.a"
cfg.DomainExactMatchARecord = "x.y.z.a"
                              ↑ココに本 VM サーバーのグローバル IPv4 アドレスを書く。
```

その後、IPA_DN_WildCardDnsServer の設定ファイル `config.go` の内容を変更した場合は、IPA_DN_WildCardDnsServer デーモンの再起動 (面倒であれば VM の再起動) が必要である。そして、再起動後には、必ず、正しく動作しているかどうか十分よく確認すること。詳しくは、https://github.com/IPA-CyberLab/IPA_DN_WildCardDnsServer/ を参照すること。


## DNS サーバー側の IP アドレスの設定 (IPA_DN_WildCardDnsServer を使用せず、一般的な DNS サーバーソフトウェアや DNS サービスプロバイダのマネージド DNS ゾーン運用サービスを利用している場合)
IPA_DN_WildCardDnsServer を使用せず、通常の DNS サーバー (例: BIND, Microsoft DNS, PowerDNS, NSD, AWS Route 53、その他の各種の DNS サービスプロバイダの DNS サーバー) で DNS ドメインのゾーンを運営している場合は、その DNS 権威サーバーにおいて、本 IPA_DN_WildcardCertServerUtil プログラムを動作させる 1 台の DNS 更新・証明書ファイル提供サーバーを指す A レコードを示す `_acme-challange.example.org` という名前の NS レコードを適切に設定すること。

- ここで、NS レコードというものは、ホスト名を指定するものであるため、IPv4 アドレスを直接指定することはできない。
- まず、A レコードとして、たとえば `ssl-cert-server.example.org` という名前のレコードを定義し、ここに本サーバーの IPv4 アドレスを記載するべきである。
- 次に、NS レコードとして、`_acme-challange.example.org` というレコード名を定義し、これの NS の値として `ssl-cert-server.example.org` というような名前の先ほど定義した A レコードを指定するべきである。
- ここで例として掲げた `ssl-cert-server.example.org` は、簡単のために、同じドメイン名である `.example.org` の配下に作成することを例示したが、実際には、異なるドメイン名の下にその A レコードを作成することでも差し支え無い。


## Web サーバー機能へのテストアクセス
上記の「DNS サーバー側の IP アドレスの設定」が完了すれば、以下の FQDN に対して、本 VM サーバーのグローバル IPv4 アドレスが解決できるようになっているはずである。

- `ssl-cert-server.example.org`  
  ※ 実際の `.example.org` の部分は、構築しようとしているドメインの名前に変更すること。

上記 A レコードに対して、いずれも、インターネットから本 VM サーバーのグローバル IPv4 アドレスが解決できることを確認すること。

問題無い場合は、任意の Web ブラウザを起動し、以下の URL にアクセスできるか確認する。

```
http://<この VM の IP アドレス>/
```

Web ブラウザで上記の URL にアクセスすると、大変うさんくさい "Index of /" のページが表示される。ここには、`wildcard_cert_files/` という単一のディレクトリがあるように見えるはずである。この `wildcard_cert_files/` にアクセスすると、Basic 認証を求められるはずである。ここで、上記の `htpasswd` で指定したユーザー名とパスワードを入力すると、空のディレクトリにアクセスできるはずである。

上記が問題なければ、nginx の稼働は成功している。


## IPA_DN_WildcardCertServerUtil プログラムのインストールとテスト実行
```
# git で 本 DNS サーバープログラム (IPA_DN_WildcardCertServerUtil) をダウンロードする。
sudo mkdir -p /opt/IPA_DN_WildcardCertServerUtil/
sudo chown ubuntu:ubuntu /opt/IPA_DN_WildcardCertServerUtil/
cd /opt/IPA_DN_WildcardCertServerUtil/
git clone --recursive https://github.com/IPA-CyberLab/IPA_DN_WildcardCertServerUtil.git

# 本 DNS 証明書更新プログラムをテスト実行をしてみる。
sudo /usr/bin/env python3 /opt/IPA_DN_WildcardCertServerUtil/IPA_DN_WildcardCertServerUtil/Main.py 【ドメイン名】 --force

# 糸冬了！！
```

上記のテスト実行を行なうと、画面にダラダラと Let's Encrypt によるワイルドカード証明書発行の様子が表示される。この過程で、Docker が活用され、認証用の一時的な DNS サーバーが立ち上がったり、ACME.sh スクリプトが呼び出されたりするなど、色々と複雑なことが行なわれる。

すべて成功すると、

```
Checking the '/var/ipa_dn_wildcard/issued_certs/<ドメイン名>/fullchain.cer' contents...
Checking the '/var/ipa_dn_wildcard/issued_certs/<ドメイン名>/<ドメイン名>.key' contents...
Issued cert files are OK.
```

という具合のメッセージが表示され、証明書の発行に成功したことが分かる。

失敗するとエラーメッセージが表示されるので、そのエラーメッセージを元に原因を究明すること。


## cron により証明書更新処理が必要に応じて自動実行されるようにする
上記のスクリプトのテスト実行で証明書更新が正常に完了したならば、これを cron で自動実行するように設定する。

```
# シェルスクリプトを作成する。
sudo dd of=/opt/run_ipa_dn_wildcard_util.sh <<\EOF
#!/bin/bash
echo --- Start --- >> /var/log/run_ipa_dn_wildcard_util.log
date >> /var/log/run_ipa_dn_wildcard_util.log

/usr/bin/env python3 /opt/IPA_DN_WildcardCertServerUtil/IPA_DN_WildcardCertServerUtil/Main.py 【ドメイン名】 >> /var/log/run_ipa_dn_wildcard_util.log 2>&1

echo Exit code: $? >> /var/log/run_ipa_dn_wildcard_util.log

date >> /var/log/run_ipa_dn_wildcard_util.log
echo --- Finished --- >> /var/log/run_ipa_dn_wildcard_util.log

EOF
sudo chmod 755 /opt/run_ipa_dn_wildcard_util.sh

# 上記のシェルスクリプトを cron で 1 日に 1 回実行するようにする。
# なお、証明書そのものは残り有効期限が 60 日未満になった場合にのみ更新される
# ので、cron で 1 日に 1 回実行すること自体に問題はない。
sudo tee -a /etc/crontab <<\EOF
0 4 * * * root /opt/run_ipa_dn_wildcard_util.sh
EOF

# cron の設定ファイルを再読込する。
sudo service cron stop
sudo service cron start

# 糸冬了！！
```


## 動作テスト
上記の設定が完了したら、Web ブラウザで

```
https://ssl-cert-server.example.org/
  ※ ↑ 実際の `.example.org` の部分は、構築しようとしているドメインの名前に変更すること。
```

にアクセスする。

以下の点を確認する。

1. 上記の HTTPS URL にアクセスしたときの SSL 証明書が、Let's Encrypt によって発行されたワイルドカード証明書となっていること。(Web ブラウザで SSL 証明書エラーが表示されないこと。)
1. Web ブラウザで上記の URL にアクセスすると、トップページに、うさんくさい "Index of /" のページが表示されること。
1. ここには、`wildcard_cert_files/` という単一のディレクトリがあるように見えるはずである。この `wildcard_cert_files/` にアクセスすると、Basic 認証を求められるはずである。ここで、上記の `htpasswd` で指定したユーザー名とパスワードを入力すると、ドメイン名のディレクトリにアクセスできること。
1. ドメイン名のディレクトリ内に `YYYYMMDD_HHMMSS` 形式のディレクトリと、`latest` というディレクトリがあること。
1. `latest` ディレクトリに、最新の Let's Encrypt ワイルドカード証明書の cer ファイル、conf ファイル、csr ファイル、key ファイルおよび `timestamp.txt` が保存されていること。これらのファイルを、組織内の任意のプログラムやサーバーからダウンロードして利用すればよい。


## 定期的なチェック
定期的に以下をチェックすること。

1. Linux 再起動後も、nginx Web サーバーが正しく自動起動して動作すること。
1. 上記で設定した cron プログラムで呼び出される本プログラムが正しく動作していること。  
   cron プログラムで呼び出される本プログラムのログファイルは、 `/var/log/run_ipa_dn_wildcard_util.log` に保存される。このファイルを定期的にチェックし、おかしなエラーが発生していないことを確認すること。
1. Web サーバーの `wildcard_cert_files/` 内のドメイン名のディレクトリの `YYYYMMDD_HHMMSS` 形式のディレクトリが、おおむね 1 ヶ月に 1 回最新のものに更新されていること。(Let's Encrypt のワイルドカード証明書の更新が正しく行なわれていること。)  
  万一、前回からの証明書更新からの更新間隔が 31 日以上空いていれば、何か異常が発生していることになるので、ログをチェックすること。
1. Web サーバーの `wildcard_cert_files/` 内のドメイン名のディレクトリの `latest/` ディレクトリに、最新の証明書が入っていること。  





