# oh-my-google

在 VPS 轻松部署 Google 镜像

---

### Depends
* Python3  
* gevent  
* requests

### Usage
* Install Python3 and pip;

* Install gevent and requests:
> sudo pip3 install -U gevent requests

* Clone oh-my-google:
> git clone git@github.com:bieberg0n/oh-my-google.git  
> cd oh-my-google

* Edit ohmygoogle.json:
> cp ohmygoogle_example.json ohmygoogle.json  
> nano ohmygoogle.json

* Run:
> ./start.sh

PS: You can use Byobu,Supervisor or other ways to background it.
