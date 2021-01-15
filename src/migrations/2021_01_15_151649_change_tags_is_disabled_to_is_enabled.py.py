from orator.migrations import Migration


class ChangeTagsIsDisabledToIsEnabled.py(Migration):

    def up(self):
        """
        Run the migrations.
        """
        with self.schema.table('tags') as table:
            # run ('UPDATE tags SET is_enabled = NOT is_disabled')
			table.boolean('is_enabled').default(True)
			
            

    def down(self):
        """
        Revert the migrations.
        """
        with self.schema.table('tags') as table:
			table.drop_column('is_enabled')
            
            