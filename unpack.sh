
echo "Backing up poc dir"

cd ~/poc
tar --exclude='.pytest_cache' --exclude='.git' --exclude='.gitignore' --exclude='.vscode'  -czvf /tmp/vm.tar.gz -C ./ .

mkdir ~/backups
mv /tmp/vm.tar.gz ~/backups/


cd ~
rm -r poc_bak
mv poc poc_bak
mkdir -p poc

cp buffer/*.gpg poc/
cd poc
gpg --output project_20240518_1534.tar.gz --decrypt project_20240518_1534.tar.gz.gpg && tar -xf project_20240518_1534.tar.gz
rm *tar*
echo "Prior poc directory is now in ~/poc_bak"

