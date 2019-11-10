
if [ -d "for_deploy" ]; then
    rm -rf for_deploy
fi

mkdir for_deploy
cd for_deploy
git clone https://github.com/lzane/blog
cd blog
./build.sh
python3 ./deploy.py
cd ../..
rm -rf for_deploy