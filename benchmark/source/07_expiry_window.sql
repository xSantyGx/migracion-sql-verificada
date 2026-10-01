CREATE OR ALTER PROCEDURE dbo.expiry_window
@from_date date, @to_date date
AS
BEGIN
 SET NOCOUNT ON;
 SELECT id,end_date FROM dbo.policies WHERE end_date BETWEEN @from_date AND @to_date ORDER BY id;
END;
