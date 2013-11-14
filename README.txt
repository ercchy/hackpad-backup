Google translate of the original text (at the bottom):

Now g0v too many things to put hackpad, in addition to its own history hackpad function should additionally be backed up

# Backup
If g0v or open source related project, I can help backup. , Please contact me.
ps if it is relatively large site, please open the admin to me, because hackpad to list uplodated pads to admin

# Profile:
( You can use # denotes comment)
- Backup_list.txt
  Line of a project to be backed up , for example g0v / *
  * Is currently not supported not
  Not the admin can, but less efficient , to loop all pads
- Api_keys.txt
  Hackpad used to access the api key, one per line , in the format as
  [key] [secret] [site]

# Api key
In hackpad site settings can be found in Note The key is for each domain separately .

# Use
Set a good backup_list.txt with api_keys.txt, execution
  python hackpad-backup.py
To

Program in data / [site] Directory Creation git repository, to padid.html as filename commit to git go .

# Feature & limitation
- Will be part of the historical versions of backup versions, but does not back up all versions , or too
- If the entire pad is deleted , the backup program does not know that it will not be deleted before the backup version basket
- The default backup in html format because this format to retain more information

===
現在 g0v 太多東西放 hackpad, 除了 hackpad 自己的 history 功能, 應該另外作備份

# 備份
如果是 g0v 或是 open source 相關 project, 我可以幫忙 backup. 請聯絡我.
p.s. 如果是比較大的 site, 請開 admin 給我, 因為 hackpad 要 admin 才能 list uplodated pads

# 設定檔: 
(可以用 # 表示 comment)
- backup_list.txt 
  一行一個要備份的項目, 譬如 g0v/*
  目前不支援不是 * 的
  不是 admin 也可以, 只是比較沒有效率, 要 loop all pads
- api_keys.txt
  用來存取 hackpad 的 api key, 一行一個, 格式如
  [key] [secret] [site]

# api key
在 hackpad 網站上的 settings 裡可以找到. 注意每個 domain 的 key 是分開的.

# 使用方法
設好 backup_list.txt 跟 api_keys.txt, 執行
  python hackpad-backup.py
即可

程式會在 data/[site] 目錄建立 git repository, 以 padid.html 為檔名 commit 到 git 去.

# feature & limitation
- 會備份部份歷史版本 versions, 不過不會備份所有版本, 不然太大了
- 若整個 pad 被刪掉, 備份程式不會知道, 也不會備份刪掉前的版畚
- 預設以 html 格式備份, 因為這格式能保留比較多資訊
