# oh-my-google

在 VPS 轻松部署 Google 镜像

---

### Depends
* Python3  

### Usage
* Install Python3 and pip;
> sudo apt install python3 python3-pip

* Clone oh-my-google:
> git clone https://github.com/bieberg0n/oh-my-google.git  
> cd oh-my-google

* Install requires:
> sudo pip3 install -U -r requirements.txt

* Edit ohmygoogle.json:
> cp ohmygoogle_example.json ohmygoogle.json  
> nano ohmygoogle.json

* Run:
> sudo ./ohmygoogle.py

PS: You can use Byobu,Supervisor or other ways to background it.
