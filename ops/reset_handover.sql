UPDATE handovers SET status = 'pending', assigned_to = NULL, assigned_to_name = NULL 
WHERE id = '7b5a441f-9837-44ce-a24a-2c9272bed473';

SELECT id, status, assigned_to FROM handovers WHERE id = '7b5a441f-9837-44ce-a24a-2c9272bed473';
