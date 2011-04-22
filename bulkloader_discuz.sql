Article:

SELECT cdb_threads.tid, cdb_threads.subject, cdb_posts.message, cdb_posts.htmlon, cdb_posts.bbcodeoff, cdb_threads.dateline, cdb_threadtypes.name, cdb_threads.views, cdb_threads.replies
	FROM cdb_threads
		JOIN cdb_posts
		JOIN cdb_threadtypes
	WHERE cdb_posts.authorid = 1
		AND cdb_posts.first = 1
		AND cdb_threads.tid = cdb_posts.tid
		AND cdb_threadtypes.typeid = cdb_threads.typeid

SELECT cdb_threads.tid, cdb_threads.subject, cdb_posts.message, cdb_posts.htmlon, cdb_posts.bbcodeoff, cdb_threads.dateline, cdb_threads.views, cdb_threads.replies
	FROM cdb_threads
		JOIN cdb_posts
	WHERE cdb_posts.authorid = 1
		AND cdb_posts.first = 1
		AND cdb_threads.tid = cdb_posts.tid
		AND cdb_threads.typeid = 0


Comment:

SELECT cdb_posts.pid, cdb_posts.tid, cdb_members.email, cdb_posts.message, cdb_posts.htmlon, cdb_posts.bbcodeoff, cdb_posts.dateline
	FROM cdb_threads
		JOIN cdb_posts
		JOIN cdb_members
	WHERE cdb_posts.authorid = 1
		AND cdb_posts.first = 0
		AND cdb_posts.tid = cdb_threads.tid
		AND cdb_posts.authorid = cdb_members.uid


User:

SELECT cdb_members.username, cdb_members.email, cdb_memberfields.site
	FROM cdb_members
		JOIN cdb_memberfields
	WHERE cdb_members.posts > 0
		AND cdb_members.uid = cdb_memberfields.uid
