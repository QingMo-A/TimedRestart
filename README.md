# TimedRestart ( 定时重启 ) 

> 一个简单的定时重启插件, 你可以自定义时区, 自定义重启时间点以及提前多久告知 ! ! !

![Version](https://img.shields.io/badge/version-v1.0.0-blue)

## 介绍

这个插件可以定时重启释放内存, 防止服务器因内存原因崩溃

## 使用

### 指令

1. 重载配置文件：
   ```java
   !!timed_restart reload
2. 列出全部指令：
   ```java
   !!timed_restart help
3. 列出当前重启时间点：
   ```java
   !!timed_restart list
4. 增加重启时间点：
   ```java
   !!timed_restart add <time>
5. 移除重启时间点：
   ```java
   !!timed_restart remove <time>
6. 更改时区：
   ```java
   // timed_restart timezone 8 -> UTC+8
   // timed_restart timezone -5 -> UTC-5
   !!timed_restart timezone <timezone>
### 配置文件 ( config/timed_restart/config.json )
默认: 
   ```json
  {
    "restart_times": [
        "06:00",
        "12:00",
        "18:00",
        "00:00"
    ],
    "warning_minutes": [
        5,
        3,
        1
    ],
    "timezone": 8
}
