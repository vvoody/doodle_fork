appcfg.py download_data --application=YOUR_APPID --config_file=bulkloader.yaml --filename=dontupload/Article.xml --kind=Article --batch_size=30 --rps_limit=1000 --url==http://YOUR_APPID.appspot.com/_ah/remote_api

appcfg.py download_data --application=YOUR_APPID --config_file=bulkloader.yaml --filename=dontupload/Comment.xml --kind=Comment --batch_size=100 --rps_limit=1000 --url==http://YOUR_APPID.appspot.com/_ah/remote_api

appcfg.py download_data --application=YOUR_APPID --config_file=bulkloader.yaml --filename=dontupload/User.xml --kind=User --batch_size=100 --rps_limit=1000 --url==http://YOUR_APPID.appspot.com/_ah/remote_api

; 本地调试时可以加上或改为下面这些参数，其中--num_threads=1可以避免很多错误
; You can use below parameters for export data from localhost:
; --num_threads=1  --url=http://localhost:8080/_ah/remote_api