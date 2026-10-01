CREATE OR ALTER PROCEDURE dbo.register_payment
@policy_id int, @amount decimal(19,4)
AS
BEGIN
 SET NOCOUNT ON;
 IF @amount IS NULL OR @amount<=0 THROW 50001,'INVALID_AMOUNT',1; IF NOT EXISTS(SELECT 1 FROM dbo.policies WHERE id=@policy_id) THROW 50002,'POLICY_NOT_FOUND',1; DECLARE @new_id int=(SELECT ISNULL(MAX(id),0)+1 FROM dbo.payments); INSERT INTO dbo.payments(id,policy_id,paid_date,amount,reference) VALUES(@new_id,@policy_id,'2024-07-01',@amount,'NEW'); SELECT @new_id AS payment_id,CAST(SUM(amount) AS decimal(19,4)) AS total_paid FROM dbo.payments WHERE policy_id=@policy_id;
END;
