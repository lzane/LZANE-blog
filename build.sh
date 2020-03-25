if [ -d "public" ]; then
    rm -rf public
fi

hugo -t cocoa --baseURL="/"
cp -r ./supplement/public/. public
cp -r ./slide public
