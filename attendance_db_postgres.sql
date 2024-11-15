CREATE TABLE Admins (
    AdminID SERIAL PRIMARY KEY,
    Email VARCHAR(50) UNIQUE,
    FirstName VARCHAR(15),
    LastName VARCHAR(15),
    Passwd CHAR(64)
);

CREATE TABLE Sessions (
    SessionID SERIAL PRIMARY KEY,
    StartTime TIMESTAMP,
    EndTime TIMESTAMP,
    AdminID INT REFERENCES Admins(AdminID)
);

CREATE TABLE Attendees (
    UniqueID SERIAL PRIMARY KEY,
    Email VARCHAR(50) UNIQUE,
    Fname VARCHAR(15),
    Lname VARCHAR(15),
    Passwd CHAR(64),
    Address VARCHAR(100)
);

CREATE TABLE AttendeesLocations (
    LocationTimestamp TIMESTAMP,
    Longitude NUMERIC(9, 6),
    Latitude NUMERIC(8, 6),
    UniqueID INT REFERENCES Attendees(UniqueID)
);

CREATE TABLE SessionLocations (
    Address VARCHAR(100),
    Longitude NUMERIC(9, 6),
    Latitude NUMERIC(8, 6),
    SessionID INT REFERENCES Sessions(SessionID),
    PRIMARY KEY (SessionID, Address, Longitude, Latitude)
);

CREATE TABLE Attended_By (
    SessionID INT REFERENCES Sessions(SessionID),
    UniqueID INT REFERENCES Attendees(UniqueID),
    PRIMARY KEY (SessionID, UniqueID)
);

-- Stored procedure for GetSessionDetails
CREATE OR REPLACE PROCEDURE GetSessionDetails(
    IN admin_id INT,
    IN end_time TIMESTAMP,
    IN student_id INT
)
LANGUAGE plpgsql
AS $$
BEGIN
    SELECT 
        s.StartTime AS starttime, 
        s.EndTime AS endtime, 
        sl.SessionID AS sid, 
        sl.Longitude AS longi, 
        sl.Latitude AS lati 
    FROM 
        SessionLocations sl
    JOIN 
        Sessions s ON s.SessionID = sl.SessionID
    JOIN 
        Attended_By ab ON ab.SessionID = s.SessionID
    WHERE 
        s.AdminID = admin_id 
        AND s.EndTime <= end_time 
        AND ab.UniqueID = student_id
    ORDER BY 
        sl.SessionID;
END;
$$;

-- Stored procedure for GetSessionDetailsForStudent
CREATE OR REPLACE PROCEDURE GetSessionDetailsForStudent(
    IN end_time TIMESTAMP,
    IN student_id INT
)
LANGUAGE plpgsql
AS $$
BEGIN
    SELECT 
        s.StartTime AS starttime, 
        s.EndTime AS endtime, 
        sl.SessionID AS sid, 
        sl.Longitude AS longi, 
        sl.Latitude AS lati 
    FROM 
        SessionLocations sl
    JOIN 
        Sessions s ON s.SessionID = sl.SessionID
    JOIN 
        Attended_By ab ON ab.SessionID = s.SessionID
    WHERE 
        s.EndTime <= end_time 
        AND ab.UniqueID = student_id
    ORDER BY 
        sl.SessionID;
END;
$$;

-- Trigger to validate attendees location
CREATE OR REPLACE FUNCTION validate_attendees_location()
RETURNS TRIGGER AS $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM Attendees WHERE UniqueID = NEW.UniqueID) THEN
        RAISE EXCEPTION 'Attendee does not exist.';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER validate_attendees_location
BEFORE INSERT ON AttendeesLocations
FOR EACH ROW
EXECUTE FUNCTION validate_attendees_location();