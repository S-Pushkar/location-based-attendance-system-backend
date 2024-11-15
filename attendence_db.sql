drop database if exists Attend_DB;
create database Attend_DB;
use Attend_DB;

create table Admins(
	AdminID INT AUTO_INCREMENT,
	primary key(AdminID),
	Email varchar(50),
	FirstName varchar(15),
	LastName varchar(15),
	Passwd char(64),
	Salt char(40)
	);
	
create table Sessions(
	SessionID INT AUTO_INCREMENT,
    primary key(SessionID),
	StartTime datetime,
	EndTime datetime,
	AdminID INT,
	foreign key(AdminID) references Admins(AdminID)
	);
	
create table Attendees(
	UniqueID INT AUTO_INCREMENT,
    primary key(UniqueID),
	Email varchar(50),
	Fname varchar(15),
	Lname varchar(15),
	Passwd char(64), /*hashed*/
	Salt char(40),
	Address varchar(100) /*expand later to AddressLine1, AddressLine2, State, City, Street, HouseNo and Zip if needed*/
	);

create table AttendeesLocations(
	LocationTimestamp timestamp,
	Longitude float(9,6),
	Latitude float(8,6),
	UniqueID INT,
	foreign key(UniqueID) references Attendees(UniqueID)
	);

create table SessionLocations(
	Address varchar(100),
	Longitude float(9,6), /* -180 to 180 */
	Latitude float(8,6), /* -90 to 90 */
	SessionID INT,
	foreign key(SessionID) references Sessions(SessionID),
	primary key(SessionID, Address, Longitude, Latitude)
	);
	
create table Attended_By(
	SessionID INT,
	UniqueID INT,
	primary key(SessionID, UniqueID),
	foreign key(SessionID) references Sessions(SessionID),
	foreign key(UniqueID) references Attendees(UniqueID)
	);

DELIMITER //

CREATE PROCEDURE GetSessionDetails(
    IN admin_id INT,
    IN end_time DATETIME,
    IN student_id INT
)
BEGIN
    SELECT 
        sessions.starttime AS starttime, 
        sessions.endtime AS endtime, 
        sessionlocations.sessionid AS sid, 
        sessionlocations.longitude AS longi, 
        sessionlocations.latitude AS lati 
    FROM 
        sessionlocations
    JOIN 
        sessions ON sessions.sessionid = sessionlocations.sessionid
    JOIN 
        attended_by ON attended_by.sessionid = sessions.sessionid
    WHERE 
        sessions.adminid = admin_id 
        AND sessions.endtime <= end_time 
        AND attended_by.uniqueid = student_id
    ORDER BY 
        sessionlocations.sessionid;
END //

DELIMITER ;

DELIMITER //

CREATE PROCEDURE GetSessionDetailsForStudent(
    IN end_time DATETIME,
    IN student_id INT
)
BEGIN
    SELECT 
        sessions.starttime AS starttime, 
        sessions.endtime AS endtime, 
        sessionlocations.sessionid AS sid, 
        sessionlocations.longitude AS longi, 
        sessionlocations.latitude AS lati 
    FROM 
        sessionlocations
    JOIN 
        sessions ON sessions.sessionid = sessionlocations.sessionid
    JOIN 
        attended_by ON attended_by.sessionid = sessions.sessionid
    WHERE 
        sessions.endtime <= end_time 
        AND attended_by.uniqueid = student_id
    ORDER BY 
        sessionlocations.sessionid;
END //

DELIMITER ;

DELIMITER //
CREATE TRIGGER validate_attendees_location
BEFORE INSERT ON AttendeesLocations
FOR EACH ROW
BEGIN
    DECLARE attendee_exists INT;
    SELECT COUNT(*) INTO attendee_exists FROM Attendees WHERE UniqueID = NEW.UniqueID;
    IF attendee_exists = 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Attendee does not exist.';
    END IF;
END;
//
DELIMITER ;
