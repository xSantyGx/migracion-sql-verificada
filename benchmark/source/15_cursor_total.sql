CREATE OR ALTER PROCEDURE dbo.cursor_total
@policy_id int
AS
BEGIN
 SET NOCOUNT ON;
 DECLARE @amount decimal(19,4),@total decimal(19,2)=0; DECLARE premium_cursor CURSOR LOCAL FAST_FORWARD FOR SELECT amount FROM dbo.premiums WHERE policy_id=@policy_id ORDER BY id; OPEN premium_cursor; FETCH NEXT FROM premium_cursor INTO @amount; WHILE @@FETCH_STATUS=0 BEGIN SET @total=@total+ISNULL(ROUND(@amount,2),0); FETCH NEXT FROM premium_cursor INTO @amount; END; CLOSE premium_cursor; DEALLOCATE premium_cursor; SELECT @total AS total;
END;
