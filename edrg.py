#!/usr/bin/python3
"""
edrg.py -- route planner for Rare Goods in Elite: Dangerous
"""

import re
import os
import xlrd           # read the excel source data file
from contextlib import contextmanager
from math import exp

from sqlalchemy import create_engine, Column, Integer, String, Float, Index, ForeignKey, func
from sqlalchemy.sql.expression import asc, desc
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.hybrid import hybrid_property, hybrid_method
from sqlalchemy.exc import IntegrityError

#base class for ORM objects
Base = declarative_base()

@contextmanager
def session_scope():
    """Provide a transactional scope around a series of operations."""
    session = Session()
    try:
        yield session
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()

def initialize_db(wipe=False):
	if wipe and os.path.isfile('edrg.sqlite'):
		os.remove('edrg.sqlite')
		
	global engine 
	global Session 
	engine = create_engine('sqlite:///edrg.sqlite', echo=False)
	Session = sessionmaker(bind=engine)
	
	if wipe:
		Base.metadata.create_all(engine)
		import_data_from_excel()

class System(Base):
	__tablename__ = 'system'
	
	id = Column(Integer, primary_key=True)
	name = Column(String, unique=True, index=True)
	x = Column(Float)
	y = Column(Float)
	z = Column(Float)
	
	stations = relationship("Station", backref="system")
	
#	@hybrid_method
	def distanceTo(self, other):
		return (((self.x - other.x) ** 2) + ((self.y - other.y) ** 2) + ((self.z - other.z) ** 2)) ** .5
	
#	@distanceTo.expression      # THIS DOESN'T WORK BECAUSE SQLITE DOESN'T HAVE THE POWER() FUNCTION
#	def distanceTo(cls, other):
#		return func.power(func.power(cls.x-other.x,2)+func.power(cls.y-other.y,2)+func.power(cls.z-other.z,2),.5)
	
	@classmethod
	def import_(cls, sheet, session):
		"""
		Import the systems from the excel spreadsheet.
		"""
		# Many magic numbers here! By phrasing them as constants, hopefully it's at least easier to 
		# modify when the sheet changes.
		
		FIRST_COLUMN = column('R')
		LAST_COLUMN  = column('DU')
		X_ROW        = 11
		Y_ROW        = 12
		Z_ROW        = 13
		NAME_ROW     = 16

		for col in range(FIRST_COLUMN, LAST_COLUMN + 1): # add 1 because of range() behavior
			name = strip(get_cell_value(sheet, (NAME_ROW, col), rcformat=True))
			x    = float(get_cell_value(sheet, (X_ROW, col), rcformat=True))
			y    = float(get_cell_value(sheet, (Y_ROW, col), rcformat=True))
			z    = float(get_cell_value(sheet, (Z_ROW, col), rcformat=True))
			
			System.add(session, name, x, y, z)
		
	@classmethod
	def add(cls, session, name, x, y, z):
		if session.query(System).filter_by(name=name).count() == 0:
			session.add(System(name=name, x=x, y=y, z=z))
		
		
class Station(Base):
	__tablename__ = 'station'
	
	id = Column(Integer, primary_key=True)
	name = Column(String)
	dist = Column(Float)
	
	system_id = Column(Integer, ForeignKey('system.id'))
	goods = relationship("Goods", backref="station")
	
	Index('ix_name_system', 'name', 'system', unique=True)
	
	@classmethod
	def import_(cls, sheet, session):
		FIRST_ROW = 17
		LAST_ROW  = 124
		NAME_COL   = 'P'
		SYSTEM_COL = 'Q'
		DIST_COL   = 'M'
		
		for row in range(FIRST_ROW, LAST_ROW + 1): # add 1 for range behavior
			name = strip(get_cell_value(sheet, NAME_COL   + str(row)))
			sys  = strip(get_cell_value(sheet, SYSTEM_COL + str(row)))
			dist = float(get_cell_value(sheet, DIST_COL   + str(row)))
			
			system = session.query(System).filter_by(name=sys).first()
			
			Station.add(session, name, system, dist)
		
	@classmethod
	def add(cls, session, name, system, dist):
		session.add(Station(name=name, dist=dist, system=system))
	
class Goods(Base):
	__tablename__ = 'goods'
	
	id = Column(Integer, primary_key=True)
	name = Column(String)
	max_cap = Column(Integer)
	min_supply = Column(Integer)
	max_supply = Column(Integer)
	price = Column(Integer)
	
	station_id = Column(Integer, ForeignKey('station.id'))
	
	Index('ix_name_station', 'name', 'station', unique=True)
	
	@hybrid_property
	def expected_supply(self):
		return round((self.min_supply + self.max_supply) / 2)
	
	@expected_supply.expression
	def expected_supply(cls):
		return func.round((cls.min_supply + cls.max_supply) / 2)
	
	@hybrid_property
	def min_value(self):
		return self.price * self.min_supply
		
	@hybrid_property
	def max_value(self):
		return self.price * self.max_supply
		
	@hybrid_property
	def expected_value(self):
		return self.price * self.expected_supply
		
	@classmethod
	def import_(cls, sheet, session):
		FIRST_ROW = 17
		LAST_ROW  = 124
		STATION_COL = 'P'
		SYSTEM_COL  = 'Q'
		NAME_COL    = 'L'
		MAX_CAP     = 'A'
		SUP_RATE    = 'B'
		MIN_SUPPLY  = 'C'
		MAX_SUPPLY  = 'D'
		PRICE       = 'K'
		
		for row in range(FIRST_ROW, LAST_ROW + 1): # add 1 for range behavior
			row = str(row)
			name = strip(get_cell_value(sheet, NAME_COL    + row))
			stt  = strip(get_cell_value(sheet, STATION_COL + row))
			sys  = strip(get_cell_value(sheet, SYSTEM_COL  + row))
			
			mc = get_cell_value(sheet, MAX_CAP    + row)
			if isinstance(mc, float):
				max_cap = round(mc)
			elif mc == 'ND':
				max_cap = 0
			elif '-' in str(mc):
				max_cap = round(float(mc[:mc.index('-')]))
			elif mc.endswith(' t'):
				max_cap = round(float(mc[:-2]))
					
			if strip(get_cell_value(sheet, SUP_RATE + row)).upper() == 'ND':
				min_supply = 0
				max_supply = 0
			else:
				min_supply = round(float(get_cell_value(sheet, MIN_SUPPLY + row)))
				max_supply = round(float(get_cell_value(sheet, MAX_SUPPLY + row)))
				
			price      = round(float(get_cell_value(sheet, PRICE      + row)))
			
			system  = session.query(System).filter_by(name=sys).first()
			station = session.query(Station).filter_by(system=system, name=stt).first()
			
			Goods.add(session, station, name, max_cap, min_supply, max_supply, price)
		
	@classmethod
	def add(cls, session, station, name, max_cap, min_supply, max_supply, price):
		session.add(Goods(station=station, name=name, max_cap=max_cap, min_supply=min_supply, max_supply=max_supply, price=price))
		
	def __str__(self):
		ev = self.expected_value
		return "{} ({}, {}): {}".format(self.name, self.station.name, self.station.system.name, ev)
	
def import_data_from_excel(path="elite dangerous rare goods.xlsx"):
	with xlrd.open_workbook(path) as book:
		sheet = book.sheet_by_index(0)
		
		with session_scope() as session:
			System.import_(sheet, session)
			Station.import_(sheet, session)
			Goods.import_(sheet, session)
			
def column(colname, exponent=0):
	"Equivalent to the Excel COLUMN() command. Given 'A', returns 1 (case insensitive)"
	if len(colname) == 0:
		return 0
	colname = colname.lower()
	alphabet = "abcdefghijklmnopqrstuvwxyz"
	return ((1 + alphabet.index(colname[-1])) * (26 ** exponent)) + column(colname[:-1], exponent+1)
	
def strip(str):
	return str.strip() # forgot it was a method
	
def tquery(q):
	"Convience method to get a scoped query"
	with session_scope() as session:
		return session.query(q)
	
def get_cell_value(sheet, address, rcformat=False):
	"""
	returns the value of the cell at the given address. 
	
	if rcformat is False, address is interpreted as a normal excel address: "H2" etc. 
	if rcformat is True,  address is interpreted as a tuple (row, column)
		The input addresses are as 1-indexed, as would be generated by Excel's ROW() and COLUMN() functions
	"""
	if rcformat:
		row, col = address
	else:
		address = address.lower()
		match = re.match(r"\A(?P<col>[a-z]+)(?P<row>[0-9]+)\Z", address)
		row =    int(match.group('row')) 
		col = column(match.group('col')) 
	row -= 1 #xlrd indexes its rows from 0, and Excel from 1
	col -= 1 #xlrd indexes its cols from 0, and Excel from 1
	return sheet.cell_value(row, col)
	
def sale_price(good, destination, p1=16000, p2=0.0677, p3=101):
	"""
	The accepted formula for sale price of a rare good in this game:
	
	    SP(x) = p0 + p1 /  ( 1.0 + exp( - ( p2 * ( x – p3 ) ) ) )
		
	OK, so what are these numbers?
	
	Guessing here based on forum speculation:
		p0 : purchase price / 2
		p1 : variable per item; related to the maximal sale price. We don't know this, so we use 
		     an estimate of 16000, which is close enough 
		p2 : galactic constant of approximately 0.0677
		p3 : galactic constant of approximately 101
		
	ref: https://forums.frontier.co.uk/showthread.php?t=66538
	"""
	
	dist = good.station.system.distanceTo(destination)
	return (good.price / 2) + (p1 / (1.0 + exp( - (p2 * (dist - p3)))))
	
def optimize(goods, outputs=1, max_dist=None, max_cargo=None):
	"""
	Accepts a list of goods. Returns the pair with the highest round-trip profit.
	"""
	
	results = []
	while len(goods) > 0:
		origin = goods.pop(0)
		for destination in goods:
			dist = origin.station.system.distanceTo(destination.station.system)
			if max_dist is None or dist <= max_dist:
				if max_cargo is None:
					oes = origin.expected_supply
					des = destination.expected_supply
				else:
					oes = origin.expected_supply if origin.expected_supply <= max_cargo else max_cargo
					des = destination.expected_supply if destination.expected_supply <= max_cargo else max_cargo
				profit_out  = oes * (sale_price(origin, destination.station.system) - origin.price)
				profit_back = des * (sale_price(destination, origin.station.system) - destination.price)
				rt_profit = profit_out + profit_back
				results.append((rt_profit, origin, destination, dist))
	
	results.sort(key=lambda ptuple: -ptuple[0]) #sorting by negative profit gives us the highest profits first
	
	for r in range(outputs):
		profit, origin, destination, dist = results.pop(0)
		print("Optimal route: "+ str(origin))
		print(" and " + str(destination))
		print(" at a distance of {:.2f} Ly with round-trip expected profit {:.0f}".format(dist, profit))
		print()
	
if __name__ == '__main__':
	import argparse
	
	parser = argparse.ArgumentParser(description="Work with the Elite Dangerous Rare Goods")
	parser.add_argument('-w', '--wipe', action='store_true', default=False,
		help="Wipe the database and recreate it from scratch from the spreadsheet")
	parser.add_argument('-c', '--count', action='store_true', default=False,
		help="Return the number of goods meeting the specified criteria")
	parser.add_argument('-d', '--display', action='store_true', default=False,
		help="Display the names of all goods meeting the specified criteria")
	parser.add_argument('-o', '--optimize', action='store_true', default=False,
		help="Compute and display the optimal route given the specified criteria")
	parser.add_argument('--optimize-outputs', action='store', default=1, type=int, metavar='N',
		help="Modifies --optimize: show the top N optimization outputs. Default 1")
	parser.add_argument('--max-dist', action='store', type=int,
		help="Modifies --optimize: the maximal distance you'll accept for a route")
	parser.add_argument('--limit-cargo', action='store', type=int, metavar='C',
		help="Modifies --optimize: calculate using at most C units of cargo, if the expected supply is greater")
	parser.add_argument('-l', '--limit', action='store', default=-1, type=int, metavar='N',
		help="Limit to the first N SQL results. This happens before optimization!")
	parser.add_argument('-f', '--filter', action='append', default=[],
		help="Raw SQLAlchemy filter strings. You have access to Goods, Station, and System.")
	parser.add_argument('-s', '--sort', action='store', 
		help="Raw SQLAlchemy order_by string. Sorts descending by default. You have access to Goods, Station, and System.")
	parser.add_argument('-a', '--ascending', action='store_true', default=False,
		help="Modifies --sort to produce an ascending sort instead.")
	
		
	ns = parser.parse_args()
	
	if not any([ns.wipe, ns.count, ns.display, ns.optimize]):
		parser.print_help()
	else:
		initialize_db(ns.wipe)
		with session_scope() as session:
			q = session.query(Goods).join(Station).join(System)
			
			# filters need to be eval'd for hybrid properties to work. Do it safely, though:
			gbs = {'__builtins__':None}
			lcs = {'Goods':Goods, 'Station':Station, 'System':System}
			for filter in ns.filter:
				q = q.filter(eval(filter, gbs, lcs))
			
			if ns.count:
				print(q.count())
				print()
			
			if ns.sort is not None:
				order = asc if ns.ascending else desc
				q = q.order_by(order(eval(ns.sort, gbs, lcs)))
				
			if ns.limit != -1:
				q = q.limit(ns.limit)
			
			if ns.display:
				for result in q.all():
					print(str(result))
				print()
				
			if ns.optimize:
				optimize(q.all(), ns.optimize_outputs, ns.max_dist, ns.limit_cargo)
	
	#TODO: work on the optimization logic, which after all was the whole point