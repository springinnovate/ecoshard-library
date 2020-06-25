import argparse
import sqlalchemy
print(sqlalchemy.__version__)

parser = argparse.ArgumentParser(description='Connect to DB')
parser.add_argument('db_user', type=str)
parser.add_argument('db_password', type=str)
parser.add_argument('db_server', type=str)
args = parser.parse_args()

engine = sqlalchemy.create_engine(
    f'postgres://{args.db_user}:{args.db_password}@{args.db_server}') # connect to server
engine.execute("CREATE DATABASE dbname") #create db
engine.execute("USE dbname") # select new db
