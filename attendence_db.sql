drop database if exists Attend_DB;
create database Attend_DB;
use Attend_DB;

create table Admins(
	AdminID char(10),
	primary key(AdminID),
	Email varchar(50),
	FirstName varchar(15),
	LastName varchar(15),
	Passwd char(64) /*hashed*/
	);
	
create table Sessions(
	SessionID char(10),
    primary key(SessionID),
	StartTime datetime,
	EndTIme datetime,
	AdminID char(10),
	foreign key(AdminID) references Admins(AdminID)
	);
	
create table Attendees(
	UniqueID char(10),
    primary key(UniqueID),
	Email varchar(50),
	Fname varchar(15),
	Lname varchar(15),
	Passwd char(64), /*hashed*/
	Address varchar(100), /*expand later to AddressLine1, AddressLine2, State, City, Street, HouseNo and Zip if needed*/
	SessionID char(10),
	foreign key(SessionID) references Sessions(SessionID)
	);

create table AttendeesLocations(
	LocationTimestamp timestamp,
	Longitude float(9,6),
	Latitude float(8,6),
	UniqueID char(10),
	foreign key(UniqueID) references Attendees(UniqueID)
	);

create table SessionLocations(
	Address varchar(100),
	Longitude float(9,6), /* -180 to 180 */
	Latitude float(8,6), /* -90 to 90 */
	SessionID char(10),
	foreign key(SessionID) references Sessions(SessionID)
	);
	