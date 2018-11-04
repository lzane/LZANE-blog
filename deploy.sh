rm -rf public
hugo -t cocoa --baseURL="https://www.lzane.com"
cp -r ./supplement/public/ public
python3 ./deploy.py  