# -*- coding: utf-8 -*-
# flake8: noqa
from qiniu import Auth, put_file, etag, CdnManager
import qiniu.config
import sys
import os 

#需要填写你的 Access Key 和 Secret Key
access_key = os.environ['QINIU_ACCESS_KEY']
secret_key = os.environ['QINIU_SECRET_KEY']

#构建鉴权对象
q = Auth(access_key, secret_key)

#要上传的空间
bucket_name = 'blog'

def myUploadFile(filePath, key):
    #生成上传 Token，可以指定过期时间等
    token = q.upload_token(bucket_name, key, 3600)
    ret, info = put_file(token, key, filePath)
    print(info)
    assert ret['key'] == key
    assert ret['hash'] == etag(filePath)

g = os.walk(r"public")  

for path,dir_list,file_list in g:  
    for file_name in file_list:  
        filePath = os.path.join(path, file_name)
        key = filePath[7:]
        myUploadFile(filePath,key)


# 刷新CDN
cdn_manager = CdnManager(q)
dirs = [
    'https://www.lzane.com/'
]
refresh_dir_result = cdn_manager.refresh_dirs(dirs)