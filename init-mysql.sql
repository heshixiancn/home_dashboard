CREATE DATABASE home_dashboard
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

CREATE USER 'home_dashboard'@'%'
  IDENTIFIED BY '请替换为强密码';

GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, INDEX, REFERENCES
ON home_dashboard.*
TO 'home_dashboard'@'%';

FLUSH PRIVILEGES;
