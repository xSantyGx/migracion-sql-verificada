CREATE OR ALTER PROCEDURE dbo.round_amount
@amount decimal(19,4), @digits int
AS
BEGIN
 SET NOCOUNT ON;
 SELECT CAST(ROUND(@amount,@digits) AS decimal(19,4)) AS rounded;
END;
