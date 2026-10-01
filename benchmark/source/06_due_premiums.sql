CREATE OR ALTER PROCEDURE dbo.due_premiums
@as_of date
AS
BEGIN
 SET NOCOUNT ON;
 SELECT id,policy_id,amount FROM dbo.premiums WHERE due_date<=@as_of ORDER BY due_date,id;
END;
