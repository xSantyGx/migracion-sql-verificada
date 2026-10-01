CREATE OR ALTER PROCEDURE dbo.get_policy
@policy_id int
AS
BEGIN
 SET NOCOUNT ON;
 SELECT id,code,annual_premium FROM dbo.policies WHERE id=@policy_id;
END;
