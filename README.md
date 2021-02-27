### 关于nproxypool
nproxypool是一个强大、灵活、高效、方便的代理池包。
Redis+aiohttp+Flask+gunicorn实现，用户只需要用相关命令创建项目，编写代理获取程序，就能在命令行启动代理池和代理获取服务。

代理池可以根据配置文件灵活的生成检测进程，针对性的检测对于某个网站的有效性，并自动维护一个代理池（有序集合）。
检测进程可以根据需要调节并发数，以维持代理池有效ip的数量合理，也同时控制检测程序对代理ip带宽的消耗。
可以设置可接受的最大响应时间，超过该响应时间的代理ip都被认为是不合格的。

实行打分制度，初始分数为60，检测合格一次直接升至100，检测不合格一次减30分，直至超过阈值就会被删除。

### nproxypool工作流程
![avatar](https://github.com/moqsien/nproxypool/blob/main/docs/proxypool.png)

### nproxypool使用方法

```bash
# 安装
bash install.sh
# or 
python setup.py build
python setup.py install

# 生成项目
npool gen example


# 编写ip获取程序
cd example
# 在my_fetcher.py中按照示例类编写自己的类即可
# edit my_fetcher.py with an editor

# 修改配置
# 修改pool.cfg中的相关配置，例如redis、gunicorn等的配置
# edit pool.cfg with an editor

# 运行命令
npool run_pool
npool run_server

# 使用代理IP
curl "http://localhost:5001/proxy/random/?key=baidu"
curl "http://localhost:5001/proxy/list/?key=baidu"
curl "http://localhost:5001/proxy/total/?key=baidu"
```

### pool.cfg配置参数说明
- [redis] redis配置
- [logfile] 日志存放目录（无需修改）
- [gunicorn] gunicorn配置（gunicorn日志目录无需修改）
- [synchronizer] 间隔多久同步一次一代池和二代池之间的ip，即把存在于二代池但是不存在于一代池中的代理IP清理掉
- [fetcher] 间隔多久从数据源获取一次代理ip
- [verifier_xxx] 检测进程配置，一个配置代表着一个检测进程，不能重名
    - name verifier的名称
    - url 用于检测的url
    - from_db 从哪个db获取代理
    - from_db_key 用于获取db的redis key，不填表示从一代池获取（因为一代池以代理ip作为key）
    - is_from_db_zset 是否是从zset中获取代理ip用于检测（从一代池中获取则为False）
    - to_db 检测完成写入那个db
    - to_db_key 写入db的哪个key中（写入一代池时，此项为空）
    - is_to_db_zset 是否是写入zset（写入一代池时，此项为False）
    - score_threshold 设置代理ip被删除时的分数最小值
    - score_decrease_by 每次检测失败之后减多少分
    - time_out 代理ip检测超时时间，越小则ip池代理响应越快
    - to_sleep 检测进程间隔多久检测一轮
    - max_worker 检测进程发送请求的并发数，越高检测越快
    
### 一代池代理ip效果图
![avatar](https://github.com/moqsien/nproxypool/blob/main/docs/first_level_pool.png)

### 二代池代理ip效果图
![avatar](https://github.com/moqsien/nproxypool/blob/main/docs/second_level_pool.png)

### 通过server获取检测后的ip效果图
![avatar](https://github.com/moqsien/nproxypool/blob/main/docs/random.png)
