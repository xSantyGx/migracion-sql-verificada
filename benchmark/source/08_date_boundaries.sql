CREATE OR ALTER PROCEDURE dbo.date_boundaries
@from_date date, @to_date date
AS
BEGIN
 SET NOCOUNT ON;
 SELECT DATEDIFF(day,@from_date,@to_date) AS days,DATEDIFF(month,@from_date,@to_date) AS months;
END;
