
if [ -d "for_deploy" ]; then
    rm -rf for_deploy
fi

mkdir for_deploy
cd for_deploy
git clone https://github.com/lzane/blog
cd blog
hugo -t cocoa --baseURL="https://www.lzane.com"
cp -r ./supplement/public/ public
python3 ./deploy.py
cd ../..
rm -rf for_deploy