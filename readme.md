## ldapsearch用法
- 通过工号查询员工信息:

```
ldapsearch -H ldap://domain.com -D "cn=administrator,cn=users,dc=domain,dc=com" -w admin_password -b dc=domain,dc=com employeeId=1000001
```

## 用法
- 打包镜像
```
docker build -t ad-operations:latest .
```

- 运行
```
docker-compose up -d
```

- 访问
打开浏览器，输入`http://<server_ip>:5000`


## 修改密码功能需要连接ad的用户有修改密码的权限
