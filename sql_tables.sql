CREATE DATABASE aiscrooge;

CREATE TABLE  article(
    id SERIAL PRIMARY KEY,
   	link TEXT,
	title TEXT,
    text TEXT,
    datetime TIMESTAMP
);